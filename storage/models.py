# encoding: utf-8

from django.db import models


class BaseModel(models.Model):
    """Base class for all models"""
    created_time = models.DateTimeField("date created", auto_now_add=True)
    last_modified_time = models.DateTimeField("last-modified", auto_now=True, db_index=True)

    class Meta:
        abstract = True


class Book(BaseModel):
    """
    The new main storage for books; the motivation for this new object is that books may be referred to by their book ID
    as provided by the publisher, but may contain different versions. So in our previous implementation of the Book
    object, we made the underlying assumption that the publisher ID would be able to uniquely identify a book.
    Unfortunately, the updates proved this assumption wrong and while the publisher ID still refers to a book, we now
    need to consider the tuple (id, version) as the unique identifier.
    """
    book_id = models.CharField(
        max_length=30,
        help_text="The primary identifier of this title, we get this value from publishers."
    )
    description = models.TextField(
        blank=True,
        null=True,
        default=None,
        help_text="Very short description of this book."
    )
    title = models.CharField(
        max_length=128,
        help_text="The title of this book.",
        db_index=True,
        null=False,
        blank=False
    )
    version = models.CharField(max_length=10, db_index=True, help_text="The version of the book.")

    def __unicode__(self):
        return u"{0} - version {1}".format(self.title, self.version)

    class Meta:
        ordering = ["title", "version"]
        unique_together = (("id", "version"), )


class Alias(BaseModel):
    """
    A book can have one or more aliases which

    For example, a book can be referred to with an ISBN-10 (older, deprecated scheme), ISBN-13 (newer scheme),
    or any number of other aliases.

    We consider the tuple (scheme, value) as a unique identifier for an Alias.
    """
    book = models.ForeignKey(Book, related_name="aliases")
    scheme = models.CharField(max_length=40, help_text="The scheme of identifier")
    value = models.CharField(max_length=255, db_index=True, help_text="The value of this identifier")

    def __unicode__(self):
        return u"Book: {0}, ID Scheme: {1}, Value: {2}".format(unicode(self.book), self.scheme, self.value)

    class Meta:
        unique_together = (("book", "value"), )


class UpdateIssues(BaseModel):
    """
    The base class for incoming updates that will track problematic data and allow us to go back and alter the
    strategies used to deal with the problems in the given data.

    This is to be subclassed to specify what type of issue is being reported.
    """
    source_file = models.CharField(max_length=255, help_text="The filename of the XML that contains the issue.")

    class Meta:
        abstract = True


class AliasUsedAsBookIdIssue(UpdateIssues):
    """
    The updates shattered some assumptions of ours - one of which is that the publisher ID will be correct. In the first
    update file (update-1.xml), we can see that this file erroneously uses the ISBN-10 as the ID for book-1. One could
    argue that we might want to resolve this by searching :class:`Alias` objects and if it matches, using the book ID
    that the alias points to. Unfortunately, in update-3.xml, we can see that it erroneously uses a proprietary alias
    for book-2.

    So we choose to only use the alias to resolve the book ID if it's an ISBN, which we trust as a universal identifier.
    If it's a proprietary identifier scheme, the updates have shown that we can't trust this, we need to find another
    method to resolve the book id.

    We want to record this decision to use the alias to resolve the book ID so that should another update render this
    resolution strategy infeasible, we can go back and clean up any mistakes that it might introduce.
    """
    alias_used = models.ForeignKey(Alias)
    book_resolved = models.ForeignKey(Book)


class AliasUsedToResolveBookIdIssue(UpdateIssues):
    """
    The updates also introduced the possibility of a book ID referring to something completely wrong, as was the case in
    update-3.xml where its identifier pointed to a proprietary identifier for book-2. We choose to resolve the book ID
    from its aliases, as this at least corrects the data that we've seen, but we know we have to be cautious because
    the aliases can be flaky as well, such in update-2 where its ISBN-13 points to book-1.

    This is our last resort for book ID resolution because of this flakiness. Still, it does the job given the knowledge
    that we're privy to, but we know that future updates could make this method problematic. Thus, we mark which ones we
    resolved via aliases.
    """
    alias_used = models.ForeignKey(Alias)
    book_resolved = models.ForeignKey(Book)


class AliasPointsToConflictingBookIssue(UpdateIssues):
    """
    Another assumption that the updates challenged was that each :class:`Alias` would point to the proper book. In
    update-2.xml we can see that we receive an ISBN-13 book-2 that actually points to book-1. This shows us that we need
    to be careful and check that our aliases point to the book that think it does before writing the alias.

    In a similar vein to how we resolve aliases being used as book IDs erroneously, we choose to not save the bad alias
    and instead mark it as such in case we need to find backtrack bad aliases or if another update comes and makes this
    strategy a poor choice. Again, we mark these bad values so that if we need to handle them differently in the future
    or change this strategy, we will be able to do so.
    """
    book = models.ForeignKey(Book)
    scheme = models.CharField(max_length=40, help_text="The scheme of identifier")
    value = models.CharField(max_length=255, db_index=True, help_text="The value of this identifier")


class VersionUnspecifiedIssue(UpdateIssues):
    """
    We also learned that versions may be missing from the data. This is problematic because we know we need to version
    the books, as previous updates have taught us. One possibility is to see if we have a previous book of the same ID,
    check its version and increment it. From both the initial set of data and the updates, this decision seems
    reasonable.

    However, it's possible that in the future we will receive an earlier version and this increment strategy won't work.
    For example, if we have the 5th edition on file and we receive an update for the 4th edition that fails to mark its
    version in the XML. In this case, we would erroneously mark it as the 6th edition. Furthermore, this strategy also
    assumes that the versions are floating point numbers. Again, given the initial set of data and the updates, this
    will work and will correctly integrate the updates. However, it's possible that this might also change, if for
    example we receive an XML file with the version as "20th anniversary edition" or some other clearly textual value.
    So again, we choose to mark what we've done so that should our understanding of the data change, we can make
    corrections as the business needs.
    """
    book_id = models.CharField(max_length=30, help_text="The book identifier.")