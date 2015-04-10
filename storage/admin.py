from django.contrib import admin

from storage.models import (
    Alias,
    AliasUsedAsBookIdIssue,
    AliasUsedToResolveBookIdIssue,
    AliasPointsToConflictingBookIssue,
    Book,
    VersionUnspecifiedIssue
)


class InlineAliasAdmin(admin.StackedInline):
    model = Alias
    extra = 0


class AliasPointsToConflictingBookAdmin(admin.ModelAdmin):
    list_display = ["book", "source_file", "scheme", "value"]


class AliasUsedAsBookIdAdmin(admin.ModelAdmin):
    list_display = ["alias_used", "book_resolved", "source_file"]


class AliasUsedToResolveBookIdAdmin(admin.ModelAdmin):
    list_display = ["alias_used", "book_resolved"]


class VersionUnspecifiedAdmin(admin.ModelAdmin):
    list_display = ["book_id", "source_file"]


class BookEditionAdmin(admin.ModelAdmin):
    inlines = [InlineAliasAdmin]

    list_display = ["id", "title", "list_aliases"]

    def list_aliases(self, obj):
        if obj:
            return u"<pre>{0}</pre>".format(u"\n".join([o.value for o in obj.aliases.all()]))

    list_aliases.allow_tags = True

admin.site.register(AliasPointsToConflictingBookIssue, AliasPointsToConflictingBookAdmin)
admin.site.register(AliasUsedToResolveBookIdIssue, AliasUsedToResolveBookIdAdmin)
admin.site.register(AliasUsedAsBookIdIssue, AliasUsedAsBookIdAdmin)
admin.site.register(Book, BookEditionAdmin)
admin.site.register(VersionUnspecifiedIssue, VersionUnspecifiedAdmin)