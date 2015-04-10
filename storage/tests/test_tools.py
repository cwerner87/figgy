# encoding: utf-8
# Created by David Rideout <drideout@safaribooksonline.com> on 2/7/14 5:01 PM
# Copyright (c) 2013 Safari Books Online, LLC. All rights reserved.

from django.test import TestCase
from lxml import etree
from storage.models import (
    Alias,
    AliasPointsToConflictingBookIssue,
    AliasUsedAsBookIdIssue,
    AliasUsedToResolveBookIdIssue,
    Book,
    VersionUnspecifiedIssue
)
import storage.tools


class TestTools(TestCase):
    def setUp(self):
        book1 = Book.objects.create(
            book_id="book-1",
            title="Book 1",
            version="1.0"
        )

        book2 = Book.objects.create(
            book_id="book-2",
            title="Book 2",
            version="1.0"
        )

        _ = Alias.objects.create(
            book=book1,
            scheme="ISBN-10",
            value="1000000001"
        )

        _ = Alias.objects.create(
            book=book2,
            scheme="ISBN-10",
            value="1000000002"
        )

    def test_storage_tools_process_book_element_new_item(self):
        """
        Test the simple case where we are processing a new book.
        """
        xml_string = """
        <book id="12345">
            <title>A title</title>
            <aliases>
                <alias scheme="ISBN-10" value="0158757819"/>
                <alias scheme="ISBN-13" value="0000000000123"/>
            </aliases>
        </book>
        """

        xml = etree.fromstring(xml_string)
        storage.tools.process_book_element(book_element=xml, filename="book-simple.xml")

        book_edition = Book.objects.get(book_id="12345")
        self.assertEqual(book_edition.title, "A title")
        self.assertEqual(book_edition.version, "1.0", "Assert that the version was inferred to 1.0")
        self.assertEqual(Alias.objects.get(book=book_edition, scheme="ISBN-10").value, "0158757819")
        self.assertEqual(Alias.objects.get(book=book_edition, scheme="ISBN-13").value, "0000000000123")

    def test_storage_tools_process_book_element_isbn_as_id(self):
        """
        Test the case when the ISBN is used as the book ID.
        """
        xml_string = """
        <book id="1000000001">
            <title>Book 1</title>
            <version>2.0</version>
            <aliases>
                <alias scheme="ISBN-10" value="1000000001"/>
            </aliases>
        </book>
        """

        xml = etree.fromstring(xml_string)
        storage.tools.process_book_element(book_element=xml, filename="book-isbn.xml")

        books = list(Book.objects.all().filter(book_id="book-1").order_by("version"))
        self.assertEqual(len(books), 2, "Assert that both versions have been created.")
        self.assertEqual(books[-1].title, "Book 1")
        self.assertEqual(books[-1].version, "2.0", "Assert that second version was properly matched to book-1.")

        alias = Alias.objects.get(book=books[0], scheme="ISBN-10")
        alias_issue = AliasUsedAsBookIdIssue.objects.filter(alias_used=alias).get()

        self.assertEqual(
            alias_issue.alias_used,
            alias,
            "Assert that the proper alias was used to infer the book ID."
        )
        self.assertEqual(
            alias_issue.book_resolved,
            books[0],
            "Assert that the proper book was used to infer the book ID."
        )
        self.assertEqual(
            alias_issue.source_file,
            "book-isbn.xml",
            "Assert that we marked that we used the alias from the first book and which source this issue comes from."
        )

    def test_storage_tools_process_book_element_from_aliases(self):
        """
        Test the case when the book ID is resolved from the book element's aliases.
        """
        xml_string = """
        <book id="12345ABC">
            <title>Book 1</title>
            <version>2.0</version>
            <aliases>
                <alias scheme="ISBN-10" value="1000000001"/>
            </aliases>
        </book>
        """

        xml = etree.fromstring(xml_string)
        storage.tools.process_book_element(book_element=xml, filename="book-aliases.xml")

        books = list(Book.objects.all().filter(book_id="book-1").order_by("version"))
        self.assertEqual(len(books), 2, "Assert that both versions have been created.")
        self.assertEqual(books[-1].title, "Book 1")
        self.assertEqual(books[-1].version, "2.0", "Assert that second version was properly matched to book-1.")

        alias = Alias.objects.get(book=books[0], scheme="ISBN-10")
        alias_issue = AliasUsedToResolveBookIdIssue.objects.filter(alias_used=alias).get()

        self.assertEqual(
            alias_issue.alias_used,
            alias,
            "Assert that the proper alias was used to resolve the book ID."
        )
        self.assertEqual(
            alias_issue.book_resolved,
            books[0],
            "Assert that the first book is marked as being the book we resolved to."
        )
        self.assertEqual(
            alias_issue.source_file,
            "book-aliases.xml",
            "Assert that we marked that we used the alias from the first book and which source this issue comes from."
        )

    def test_storage_tools_process_book_element_with_conflicting_alias(self):
        """
        Test the case when the book has an alias that conflicts with a different book.
        """
        xml_string = """
        <book id="book-1">
            <title>Book 1</title>
            <version>2.0</version>
            <aliases>
                <alias scheme="ISBN-10" value="1000000002"/>
            </aliases>
        </book>
        """

        xml = etree.fromstring(xml_string)
        storage.tools.process_book_element(book_element=xml, filename="book-conflict.xml")

        conflicting_book = Book.objects.get(book_id="book-2")
        alias_issue = AliasPointsToConflictingBookIssue.objects.filter(book=conflicting_book, scheme="ISBN-10").get()

        self.assertEqual(
            alias_issue.book,
            conflicting_book,
            "Assert that we marked the book as having a conflicting alias issue."
        )
        self.assertEqual(
            alias_issue.scheme,
            "ISBN-10",
            "Assert that we marked the scheme of the conflicting alias issue."
        )
        self.assertEqual(
            alias_issue.source_file,
            "book-conflict.xml",
            "Assert that we marked the source file where this issue comes from."
        )

    def test_storage_tools_process_book_element_with_inferred_version(self):
        xml_string = """
        <book id="book-1">
            <title>Book 1</title>
            <aliases>
                <alias scheme="ISBN-10" value="1000000001"/>
            </aliases>
        </book>
        """

        xml = etree.fromstring(xml_string)
        storage.tools.process_book_element(book_element=xml, filename="book-version.xml")

        books = list(Book.objects.all().filter(book_id="book-1").order_by("version"))
        self.assertEqual(len(books), 2, "Assert that both versions have been created.")
        self.assertEqual(books[-1].title, "Book 1")
        self.assertEqual(books[-1].version, "2.0", "Assert that the version was inferred to be 2.0")

        version_issue = VersionUnspecifiedIssue.objects.get(book_id="book-1")
        self.assertEqual(
            version_issue.book_id,
            "book-1",
            "Assert that the book ID with the missing version has been marked."
        )
        self.assertEqual(
            version_issue.source_file,
            "book-version.xml",
            "Assert that the version imputation was properly recorded."
        )