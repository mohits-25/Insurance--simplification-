"""
Generates a synthetic demo insurance policy PDF (fake data only) for testing
the PolicyLens AI ingestion/OCR/privacy/analysis pipeline end-to-end.

Run: python create_sample_policy.py
Produces: sample_policy.pdf (text-based) in the backend directory.
"""
import fitz

PAGES = [
    """HEALTH SHIELD INSURANCE POLICY

Policyholder Details

Name: Ravi Kumar
Policy Number: HS-2024-889231
Customer ID: CUST-4471221
Phone: 9876543210
Email: ravi.kumar@example.com
Address: 12 MG Road, Bangalore, Karnataka 560001
Aadhaar: 1234 5678 9012
PAN: ABCPK1234E
Account Number: 000123456789

This policy document explains the terms of your Health Shield health insurance plan.
""",
    """Coverage

This policy covers hospitalization expenses, pre and post hospitalization expenses for
up to 30 days before and 60 days after hospitalization, daycare procedures, and ambulance
charges up to Rs. 2,000 per hospitalization event. Coverage includes room rent, ICU charges,
doctor fees, and diagnostic tests directly related to the hospitalization.

Hospitalization

Hospitalization is covered when the insured is admitted for a minimum continuous period of
24 hours in a hospital that is registered with local authorities and has at least 10 inpatient
beds. Room rent is covered up to Rs. 5,000 per day. ICU charges are covered up to Rs. 10,000
per day.
""",
    """Waiting Period

There is an initial waiting period of 30 days from the policy start date during which no
claims are payable except for accidental hospitalization. Specific illnesses such as cataract,
hernia, and joint replacement have a waiting period of 24 months. Pre-existing diseases have
a waiting period of 36 months from the date of first policy issuance.

Deductible

A deductible of Rs. 10,000 applies per claim. The policyholder must bear this amount before
the insurer pays the remaining eligible claim amount. A co-payment of 10% applies for insured
persons above 60 years of age.
""",
    """Exclusions

The following are not covered under this policy: cosmetic or plastic surgery unless medically
necessary due to accident, dental treatment unless requiring hospitalization due to accident,
treatment for obesity or weight control, self-inflicted injuries, injuries due to participation
in adventure sports, and treatment taken outside India. Claims arising from war, nuclear risks,
or participation in illegal activities are also excluded.

Any treatment related to infertility or maternity is excluded unless a maternity rider has been
purchased separately.
""",
    """Claim Procedure

For cashless claims, the insured must present the health card at a network hospital and obtain
pre-authorization at least 48 hours before planned hospitalization, or within 24 hours for
emergency admission. For reimbursement claims, the insured must submit the claim form, original
bills, discharge summary, and diagnostic reports within 30 days of discharge.

Coverage Limits

The maximum sum insured under this policy is Rs. 5,00,000 per policy year. Room rent is capped
at 1% of sum insured per day. Ambulance charges are capped at Rs. 2,000 per hospitalization.

Renewal

This policy is renewable annually up to age 65, subject to timely payment of premium. A grace
period of 30 days is allowed for renewal after the due date. No claims are payable for treatment
taken during the grace period before renewal is completed.

Conditions

The insured must disclose all pre-existing medical conditions at the time of proposal. Failure
to disclose material facts may result in claim rejection or policy cancellation. The insurer
reserves the right to request an independent medical examination.

Important Definitions

Sum Insured means the maximum amount payable by the insurer during a policy year. Network
Hospital means a hospital which has an agreement with the insurer for providing cashless
treatment. Pre-existing Disease means any condition diagnosed or for which treatment was
sought within 48 months prior to the policy start date.
""",
]


def build_pdf(output_path: str = "sample_policy.pdf"):
    doc = fitz.open()
    for page_text in PAGES:
        page = doc.new_page(width=595, height=842)  # A4
        rect = fitz.Rect(50, 50, 545, 792)
        page.insert_textbox(rect, page_text, fontsize=11, fontname="helv")
    doc.save(output_path)
    doc.close()
    print(f"Sample policy PDF created at: {output_path}")


if __name__ == "__main__":
    build_pdf()
