# encoding: utf-8
# Created by David Rideout <drideout@safaribooksonline.com> on 2/7/14 4:58 PM
# Copyright (c) 2013 Safari Books Online, LLC. All rights reserved.

from storage.models import (
    Alias,
    AliasPointsToConflictingBookIssue,
    AliasUsedAsBookIdIssue,
    AliasUsedToResolveBookIdIssue,
    Book,
    VersionUnspecifiedIssue
)


def _fetch_book_id_by_aliases(aliases, source_file):
    """
    Attempt to resolve a book ID by the aliases given in the XML for the book. This is the last resort for book ID
    resolution but it solves the issue of the book ID pointing to something completely nonsensical by making a
    best-effort resolution from its aliases. For example, in update-3.xml, it uses the proprietary alias for an entirely
    different book as its ID. In this case, no other resolution will succeed, so we check what its aliases point to.

    :param aliases:
        The list of all <alias> elements for the book.
    :return:
        The matching book identifier, if one exists, otherwise None.
    """
    for alias in aliases:
        scheme, value = alias.get("scheme"), alias.get("value")
        existing_alias = Alias.objects.filter(scheme=scheme, value=value).first()

        # If we match with an existing alias, use it to get the book ID and mark our decision with this book and which
        # source file introduced the issue
        if existing_alias is not None:
            alias_resolution, _ = AliasUsedToResolveBookIdIssue.objects.get_or_create(
                alias_used=existing_alias,
                book_resolved=existing_alias.book,
                source_file=source_file
            )
            alias_resolution.save()

            return existing_alias.book.book_id

    return None


def _fetch_book_id_by_scheme(scheme, source_file, value):
    """
    Attempt to resolve a book ID by a particular alias scheme (i.e. ISBN-10, ISBN-13). This is for when we are checking
    if the given book ID has been erroneously marked as an alias like an ISBN-10 instead of the book ID.

    :param scheme:
        The given scheme (such as ISBN-10).
    :param source_file:
        The source file we are receiving updates from in case we need to record problems.
    :param value:
        The value for the scheme (such as 1000000001).

    :return:
        The book ID if one is found, otherwise None.
    """
    alias = Alias.objects.filter(scheme=scheme, value=value).first()

    # If a book alias (i.e. an ISBN-10) is being used as the book ID, the updates have shown us that this cannot be
    # reliably used as a proxy for the book ID. What we do instead is mark that the book ID is actually an alias and
    # that the file needs manual review so we don't corrupt any data. For further discussion, see
    # :class:`AliasUsedAsBookIdIssue`.
    if alias is not None:
        alias_error, _ = AliasUsedAsBookIdIssue.objects.get_or_create(
            alias_used=alias,
            book_resolved=alias.book,
            source_file=source_file
        )
        alias_error.save()
        return alias.book.book_id

    return None


def _infer_book_version(book_id, filename, version):
    """
    Attempt to infer a book version.

    The first attempt is to get it directly from the XML element. Should it be missing, we then check if there are
    other versions of the book. If there are, we sort them by their version number and increment the newest version we
    have on file.

    We also mark whenever we have to guess by incrementing the version number of an existing version we have. We do this
    bookkeeping to mark our version resolutions should further updates prove that this was not the right decision. For
    further discussion, see :class:`VersionUnspecifiedIssue`.

    :param book_id:
        The identifier of the book.
    :param filename:
        The source file we are receiving updates from in case we need to record problems.
    :param version:
        The version from the XML file, which might be None.

    :return:
        Our inferred book version string.
    """
    try:
        # Ideally get the version number from the XML element itself
        return str(float(version))
    except (TypeError, ValueError):
        # Otherwise, get the version from an existing book we have in the system and again, mark that we made this
        # inference of the version so we can go back if need be
        version_missing_error, _ = VersionUnspecifiedIssue.objects.get_or_create(book_id=book_id, source_file=filename)
        version_missing_error.save()

        existing_books = list(Book.objects.all().filter(book_id=book_id))
        # If absolutely no books exist with this ID, mark it as 1.0
        if len(existing_books) == 0:
            return "1.0"

        # Otherwise, find the latest version and return the version + 1
        existing_books.sort(key=lambda x: -float(x.version))
        return str(float(existing_books[-1].version) + 1)


def _process_book_aliases(aliases, book, book_id, filename):
    """
    Create (if necessary) the aliases for a given book element. We take care to mark if an alias points to an existing
    book that doesn't match and from which file this erroneous alias came from.

    We also check for a previous version and if an updated version is missing any of the aliases for the previous
    version, we go ahead and fill them in. So in the case of update-2.xml, we won't lose the ISBN-13 because it has
    erroneous data.

    :param aliases:
        The list of all <alias> elements for the book.
    :param book:
        The :class:`Book` object.
    :param book_id:
        The resolved identifier for the book.
    :param filename:
        The source file we are receiving updates from in case we need to record problems.
    """
    for alias in aliases:
        scheme = alias.get("scheme")
        value = alias.get("value")

        alias = Alias.objects.filter(scheme=scheme, value=value).first()
        # If the alias already exists, check that it points to this book. If it doesn't, we need to flag this for
        # manual review.
        if alias is not None and alias.book.book_id != book_id:
            conflict_error, _ = AliasPointsToConflictingBookIssue.objects.get_or_create(
                book=alias.book,
                scheme=scheme,
                source_file=filename,
                value=value
            )
            conflict_error.save()
            continue

        book.aliases.get_or_create(scheme=scheme, value=value)
    book.save()

    # If the update has missing aliases, go ahead and use fill in any missing ones from a previous version of the book
    existing_book = Book.objects.filter(book_id=book_id).first()
    missing_aliases = list(
        set([(alias.scheme, alias.value) for alias in existing_book.aliases.all()]) -
        set([(alias.scheme, alias.value) for alias in book.aliases.all()])
    )

    for scheme, value in missing_aliases:
        book.aliases.get_or_create(scheme=scheme, value=value)

    book.save()


def _resolve_book_id(aliases, book_id, filename):
    """
    Attempt to resolve an identifier for the book. We take the following steps based on our updated levels of confidence
    about what data is reliable and what isn't:

    Check that an existing book exists with this ID, and if it does, use the ID supplied.

    Check that an ISBN-10 or ISBN-13 exist with the given ID. If one does, resolve use the book ID of the book that the
    ISBN alias points to. ISBN is a universal, non-proprietary identifier, so we have some confidence in making this
    resolution.

    Check the aliases listed in the book element for a match. If one matches, use its identifier. This is less reliable
    as we know aliases can be flaky, but is appropriate given the data we have seen and does the job adequately.

    :param aliases:
        The list of all <alias> elements for the book.
    :param book_id:
        The book ID supplied in the XML file.
    :param filename:
        The source file we are receiving updates from in case we need to record problems.

    :return:
        The resolved book identifier, or, if none can be matched, use the book identifier supplied as the ID for a new
        book object.
    """
    existing_book = Book.objects.all().filter(book_id=book_id).first()
    if existing_book is not None:
        return book_id

    # If there is no existing book or alias to help us resolve, default to a new book ID.
    return \
        _fetch_book_id_by_scheme(scheme="ISBN-10", source_file=filename, value=book_id) or \
        _fetch_book_id_by_scheme(scheme="ISBN-13", source_file=filename, value=book_id) or \
        _fetch_book_id_by_aliases(aliases=aliases, source_file=filename) or \
        book_id


def process_book_element(book_element, filename):
    """
    Process a book element into the database.

    :param book_element:
        The XML book element.
    :param filename:
        The filename of the XML - this is to mark files that have problems and need review.
    """
    book_id = book_element.get("id")
    aliases = book_element.xpath("aliases/alias")

    resolved_book_id = _resolve_book_id(aliases, book_id, filename)
    version = _infer_book_version(resolved_book_id, filename, book_element.findtext("version"))

    book, _ = Book.objects.get_or_create(book_id=resolved_book_id, version=version)
    book.title = book_element.findtext("title")
    book.description = book_element.findtext("description")
    _process_book_aliases(aliases, book, resolved_book_id, filename)

    book.save()