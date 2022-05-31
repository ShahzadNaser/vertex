# Copyright (c) 2021, The Nexperts Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.utils import getdate, formatdate, flt
from erpnext.payroll.doctype.salary_slip.salary_slip import SalarySlip


class CustomSalarySlip(SalarySlip):
    def get_data_for_eval(self):
        '''Returns data for evaluating formula'''
        # customization add cache for performance improvement
        #key = "temp_{0}".format(self.employee)
        #val = frappe.cache().get_value(key)
        #if val: return val
        data = frappe._dict()
        employee = frappe.get_doc("Employee", self.employee).as_dict()

        start_date = getdate(self.start_date)
        date_to_validate = (
            employee.date_of_joining
            if employee.date_of_joining > start_date
            else start_date
        )

        salary_structure_assignment = frappe.get_value(
            "Salary Structure Assignment",
            {
                "employee": self.employee,
                "salary_structure": self.salary_structure,
                "from_date": ("<=", date_to_validate),
                "docstatus": 1,
            },
            "*",
            order_by="from_date desc",
            as_dict=True,
        )
        if not salary_structure_assignment:
            frappe.throw(
                _("Please assign a Salary Structure for Employee {0} "
                "applicable from or before {1} first").format(
                    frappe.bold(self.employee_name),
                    frappe.bold(formatdate(date_to_validate)),
                )
            )

        emp_salary_details = get_emp_salary_components(salary_structure_assignment.get("name"))

        data.update(salary_structure_assignment)
        data.update(employee)
        data.update(self.as_dict())
        self.hourly_rate = salary_structure_assignment.get("hourly_rate")

        # set values for components
        salary_components = frappe.get_all("Salary Component", fields=["salary_component_abbr"])
        for sc in salary_components:
            data.setdefault(sc.salary_component_abbr, emp_salary_details.get(sc.salary_component_abbr) or 0)

        for key in ('earnings', 'deductions'):
            for d in self.get(key):
                data[d.abbr] = d.amount

        # customization add data in cache for performance imporvement
        #frappe.cache().set_value(key, data, expires_in_sec=100)
        return data

    # def make_loan_repayment_entry(self):
    #     from erpnext.loan_management.doctype.loan_repayment.loan_repayment import create_repayment_entry
    #     for loan in self.loans:
    #         repayment_entry = create_repayment_entry(loan.loan, self.employee,
    #             self.company, self.posting_date, loan.loan_type, "Regular Payment", loan.interest_amount,
    #             loan.principal_amount, loan.total_payment)

    #         repayment_entry.payroll_entry = self.get("payroll_entry")
    #         repayment_entry.save()
    #         repayment_entry.submit()

    #         frappe.db.set_value("Salary Slip Loan", loan.name, "loan_repayment_entry", repayment_entry.name)
    

def get_emp_salary_components(salary_structure_assignment):
    if not salary_structure_assignment:
        return {}

    esc =  frappe.db.get_list("Employee Salary Components", filters={"parent": salary_structure_assignment}, fields=["salary_component","abbr","amount"])
    emp_salary_details = {}
    for row in esc:
        if row.get("amount"):
            emp_salary_details[row.get("abbr")] = row.get("amount")

    return emp_salary_details