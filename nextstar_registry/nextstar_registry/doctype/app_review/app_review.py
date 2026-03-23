import frappe
from frappe.model.document import Document


class AppReview(Document):
    def validate(self):
        if self.rating and (int(self.rating) < 1 or int(self.rating) > 5):
            frappe.throw("Rating must be between 1 and 5")
