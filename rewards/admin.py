from django.contrib import admin
from .models import CustomerProfile, RewardsAccount, PointsLedger, EarningRule, RewardItem, Redemption, GuestCustomer, PurchaseRecord



@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "birthday", "sex", "ship_city", "ship_state", "marketing_opt_in")
    search_fields = ("user__email", "user__username", "phone", "ship_city", "ship_state")


@admin.register(RewardsAccount)
class RewardsAccountAdmin(admin.ModelAdmin):
    list_display = ("user", "points_balance", "created_at", "signup_bonus_awarded")
    search_fields = ("user__email", "user__username")


@admin.register(PointsLedger)
class PointsLedgerAdmin(admin.ModelAdmin):
    list_display = ("created_at", "account", "delta", "kind", "source", "reference")
    search_fields = ("account__user__email", "reference")
    list_filter = ("kind", "source")
    date_hierarchy = "created_at"


@admin.register(EarningRule)
class EarningRuleAdmin(admin.ModelAdmin):
    list_display = ("code", "rule_type", "multiplier", "active")
    list_filter = ("rule_type", "active")


@admin.register(RewardItem)
class RewardItemAdmin(admin.ModelAdmin):
    list_display = ("sku", "name", "points_cost", "inventory", "is_active")
    list_filter = ("is_active",)
    search_fields = ("sku", "name")


@admin.register(Redemption)
class RedemptionAdmin(admin.ModelAdmin):
    list_display = ("created_at", "account", "item", "points_spent", "fulfilled")
    list_filter = ("fulfilled",)
    date_hierarchy = "created_at"


@admin.register(GuestCustomer)
class GuestCustomerAdmin(admin.ModelAdmin):
    list_display = ("email", "phone", "first_seen", "last_seen")
    search_fields = ("email", "phone")


@admin.register(PurchaseRecord)
class PurchaseRecordAdmin(admin.ModelAdmin):
    list_display = ("created_at", "kind", "external_id", "account", "guest", "subtotal_cents", "currency")
    search_fields = ("external_id", "email", "phone")
    list_filter = ("kind", "currency")
    date_hierarchy = "created_at"