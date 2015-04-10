# encoding: utf-8
"""
Copyright (c) 2013 Safari Books Online. All rights reserved.
"""

from django.test import TestCase

from storage import models


class TestModels(TestCase):
    def setUp(self):
        self.book = models.Book.objects.create(
            book_id="book-1",
            title="The Title",
            version="1.0"
        )
        self.alias = models.Alias.objects.create(
            book=self.book,
            scheme="ISBN-10",
            value="1000000001"
        )

    def test_book_have_unicode_method(self):
        """
        The book should have a __unicode__ method that specifies the version number.
        """
        expected = u"{0} - version {1}".format(self.book.title, self.book.version)
        self.assertEquals(expected, unicode(self.book))

    def test_alias_has_unicode_method(self):
        """
        The alias should also have a __unicode__ method that specifies the book and the ID scheme and value.
        """
        expected = u"Book: {0}, ID Scheme: {1}, Value: {2}".format(unicode(self.book), u"ISBN-10", u"1000000001")
        self.assertEqual(expected, unicode(self.alias))