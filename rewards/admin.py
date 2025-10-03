# rewards/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, Count, Q
from .models import (
    CustomerProfile, RewardsAccount, PointsLedger, EarningRule,
    RewardItem, Redemption, GuestCustomer, PurchaseRecord
)

@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "birthday", "sex", "ship_city", "ship_state", "marketing_opt_in")
    search_fields = ("user__email", "user__username", "phone", "ship_city", "ship_state", "ship_postal")
    list_filter = ("sex", "marketing_opt_in")

class PointsInline(admin.TabularInline):
    model = PointsLedger
    extra = 0
    fields = ("created_at", "delta", "kind", "source", "reference")
    ordering = ("-created_at", "-id")
    readonly_fields = fields

@admin.action(description="Grant +25 pts")
def grant_25(modeladmin, request, queryset):
    for acc in queryset.select_related("user"):
        acc.apply_ledger(delta=25, kind="ADJUST", source="MANUAL", ref="admin_grant")

@admin.action(description="Deduct 25 pts")
def deduct_25(modeladmin, request, queryset):
    for acc in queryset.select_related("user"):
        acc.apply_ledger(delta=-25, kind="ADJUST", source="MANUAL", ref="admin_deduct")

@admin.register(RewardsAccount)
class RewardsAccountAdmin(admin.ModelAdmin):
    list_display = ("user", "points_balance", "created_at", "signup_bonus_awarded", "purchases_count")
    search_fields = ("user__email", "user__username")
    list_filter = ("signup_bonus_awarded",)
    inlines = [PointsInline]
    actions = [grant_25, deduct_25]

    def purchases_count(self, obj):
        return obj.purchases.count()

@admin.register(PointsLedger)
class PointsLedgerAdmin(admin.ModelAdmin):
    list_display = ("created_at", "account_user", "delta", "kind", "source", "reference")
    list_filter = ("kind", "source", "created_at")
    search_fields = ("account__user__email", "reference")
    ordering = ("-created_at", "-id")

    def account_user(self, obj):
        return obj.account.user

@admin.register(PurchaseRecord)
class PurchaseRecordAdmin(admin.ModelAdmin):
    list_display = ("created_at", "kind", "external_id", "who", "subtotal_cents", "currency")
    list_filter = ("kind", "currency", "created_at")
    search_fields = ("external_id", "email", "account__user__email", "guest__email")
    readonly_fields = ("created_at",)

    def who(self, obj):
        if obj.account_id:
            return obj.account.user.email
        return obj.email or "(guest)"

@admin.register(RewardItem)
class RewardItemAdmin(admin.ModelAdmin):
    list_display = ("sku", "name", "points_cost", "inventory", "is_active")
    list_editable = ("points_cost", "inventory", "is_active")
    search_fields = ("sku", "name")

@admin.action(description="Mark selected redemptions fulfilled")
def mark_fulfilled(modeladmin, request, queryset):
    queryset.update(fulfilled=True)

@admin.register(Redemption)
class RedemptionAdmin(admin.ModelAdmin):
    list_display = ("created_at", "account", "item", "points_spent", "fulfilled")
    list_filter = ("fulfilled", "created_at", "item")
    search_fields = ("account__user__email", "item__name")
    actions = [mark_fulfilled]

@admin.register(EarningRule)
class EarningRuleAdmin(admin.ModelAdmin):
    list_display = ("code", "rule_type", "multiplier", "active")
    list_editable = ("multiplier", "active")
    list_filter = ("rule_type", "active")

@admin.register(GuestCustomer)
class GuestCustomerAdmin(admin.ModelAdmin):
    list_display = ("email", "phone", "first_seen", "last_seen", "purchases_count")
    search_fields = ("email", "phone")
    ordering = ("-last_seen",)

    def purchases_count(self, obj):
        return obj.purchases.count()
