import frappe
from frappe.model.document import Document


class CommunityReviewer(Document):
    def validate(self):
        points = self.reputation_points or 0
        if points >= 200:
            self.badge = "Gold"
        elif points >= 50:
            self.badge = "Silver"
        else:
            self.badge = "Bronze"
