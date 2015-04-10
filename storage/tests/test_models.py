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

    def test_book_have_unicode_method(self):
        """
        The book should have a __unicode__ method that specifies the version number.
        """
        expected = u"{0} - version {1}".format(self.book.title, self.book.version)
        self.assertEquals(expected, unicode(self.book))