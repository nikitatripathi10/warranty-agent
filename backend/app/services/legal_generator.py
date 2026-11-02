"""
1-Click Legal Notice and Consumer Court (e-Daakhil / NCH 1915) Dispute Generator.
Grounding: Consumer Protection Act, 2019 (Act No. 35 of 2019).

Features:
- Formal 15-Day Statutory Legal Demand Notice.
- National Consumer Helpline (NCH 1915 / INGRAM) Complaint Draft.
- e-Daakhil (District Consumer Commission) Filing Guidance.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from app.models import Purchase
from app.schemas import LegalNoticeRequest, LegalNoticeResponse


GRIEVANCE_TITLES = {
    "warranty_denial": "Unlawful Denial/Repudiation of Legitimate Warranty Claim & Deficiency in Service",
    "defective_product": "Supply of Inherent Defective Goods & Refusal of Replacement/Repair under Statutory Warranty",
    "delayed_repair": "Unreasonable Delay (>30 Days) in Warranty Repair & Deficiency in After-Sales Service",
    "unfair_trade_practice": "Misleading Warranty Assurances, False Representations & Unfair Trade Practice",
}

GRIEVANCE_DETAILS_DEFAULT = {
    "warranty_denial": (
        "The consumer lodged a formal warranty claim after the product developed functional defects "
        "within the active warranty period. The company and authorized service representatives unlawfully "
        "repudiated and denied coverage on frivolous, unsubstantiated pretexts without conducting an unbiased technical inspection."
    ),
    "defective_product": (
        "The product suffers from severe inherent manufacturing defects and fails to perform its primary "
        "intended functions. Despite prompt notification within the warranty window, the manufacturer and retailer "
        "have failed and neglected to replace the defective unit with a defect-free product."
    ),
    "delayed_repair": (
        "The product was submitted to the authorized service center for repair under warranty. "
        "More than 30 days have elapsed without repair or return, citing non-availability of spare parts, "
        "causing substantial hardship, harassment, and deprivation of utility."
    ),
    "unfair_trade_practice": (
        "The brand and seller marketed and sold the product with representations of comprehensive warranty and "
        "service coverage. When claimed, the consumer was met with opaque exclusions and demand for exorbitant repair charges, "
        "amounting to an Unfair Trade Practice under Section 2(47) of the Consumer Protection Act, 2019."
    ),
}


def generate_legal_notice(purchase: Purchase, req: LegalNoticeRequest) -> LegalNoticeResponse:
    today_str = date.today().strftime("%d %B %Y")
    product_name = (purchase.product_name or "Consumer Product").strip()
    brand = (purchase.brand or "Manufacturer / Brand").strip()
    retailer = (purchase.retailer or "Retailer / E-Commerce Platform").strip()
    price_val = f"₹{float(purchase.price):,.2f}" if purchase.price is not None else "Consideration Amount Paid"
    purchase_date_str = purchase.purchase_date.strftime("%d %B %Y") if purchase.purchase_date else "Recorded Invoice Date"
    inv_num = (purchase.source_file_ref or purchase.source_email_id or f"WRD-INV-{str(purchase.id)[:8].upper()}")

    consumer_name = (req.consumer_name or "AGGRIEVED CONSUMER").strip()
    consumer_address = (req.consumer_address or "[Consumer Residential Address, City, State, PIN]").strip()
    consumer_phone = (req.consumer_phone or "[Consumer Mobile / Contact Number]").strip()

    grievance_key = req.grievance_type if req.grievance_type in GRIEVANCE_TITLES else "warranty_denial"
    grievance_title = GRIEVANCE_TITLES[grievance_key]
    issue_desc = (req.issue_description or "").strip() or GRIEVANCE_DETAILS_DEFAULT[grievance_key]

    notice_ref = f"WRD/LEG/{datetime.now().year}/{str(purchase.id)[:8].upper()}"

    # Statutory sections cited
    statutory_sections = [
        "Section 2(7) - Consumer status and protection rights",
        "Section 2(11) - Deficiency in Service",
        "Section 2(47) - Unfair Trade Practice",
        "Sections 84-87 (Chapter VI) - Product Liability of Manufacturer and Product Seller",
        "Section 35 - Redressal before the District Consumer Disputes Redressal Commission (e-Daakhil)",
    ]

    # Pre-Litigation Legal Notice Text
    legal_notice_text = f"""================================================================================
                    FORMAL PRE-LITIGATION LEGAL NOTICE OF DEMAND
      (UNDER SECTIONS 2(11), 2(47), AND 84-87 OF THE CONSUMER PROTECTION ACT, 2019)
================================================================================

REF. NO: {notice_ref}
DATE: {today_str}
MODE OF SERVICE: SPEED POST WITH ACKNOWLEDGEMENT DUE / REGISTERED EMAIL

TO,
1. THE MANAGING DIRECTOR / GRIEVANCE OFFICER
   {brand.upper()} (MANUFACTURER / BRAND)
   Authorized Service & Legal Redressal Division

2. THE CUSTOMER GRIEVANCE OFFICER / LEGAL DEPARTMENT
   {retailer.upper()} (PRODUCT SELLER / RETAILER)

FROM:
   {consumer_name}
   {consumer_address}
   Contact: {consumer_phone}

SUBJECT: STATUTORY NOTICE OF DEMAND FOR DEFICIENCY IN SERVICE, PRODUCT DEFECT, AND REFUSAL TO HONOR STATUTORY WARRANTY REGARDING "{product_name.upper()}".

DEAR SIR / MADAM,

UNDER INSTRUCTIONS AND WRITTEN AUTHORITY AS THE AGGRIEVED CONSUMER, THIS FORMAL PRE-LITIGATION LEGAL DEMAND NOTICE IS HEREBY SERVED UPON YOU:

1. THE COMPLAINANT IS A BONA FIDE CONSUMER:
   That I am a recognized 'Consumer' within the statutory definition of Section 2(7) of the Consumer Protection Act, 2019, having purchased the product "{product_name}" from {retailer} manufactured/marketed by {brand} on {purchase_date_str} for a valuable total sale consideration of {price_val} against Invoice/Reference No. {inv_num}.

2. STATUTORY WARRANTY & INHERENT DEFECT:
   That at the time of purchase, the opposite parties warranted and represented that the said product was brand new, free of defect, and covered under standard comprehensive manufacturer warranty. However, during the course of regular usage, the product developed severe defects and failures:
   "{issue_desc}"

3. DEFICIENCY IN SERVICE & BREACH OF OBLIGATION:
   That upon notifying your customer support and authorized service center, the opposite parties failed to redress the grievance, unlawfully refused/delayed warranty obligations, and sought to evade statutory product liability. Such deliberate conduct amounts to:
   (a) 'Deficiency in Service' under Section 2(11) of the Consumer Protection Act, 2019;
   (b) 'Unfair Trade Practice' under Section 2(47) of the Consumer Protection Act, 2019; and
   (c) Joint and Several 'Product Liability' of both Manufacturer and Product Seller under Chapter VI (Sections 84, 85, 86, and 87) of the Act.

4. FORMAL 15-DAY PEREMPTORY DEMAND:
   You are hereby called upon to immediately comply with either of the following remedies within FIFTEEN (15) DAYS of receipt of this notice:
   (a) Provide an immediate, brand-new, defect-free replacement of "{product_name}" with fresh warranty; OR
   (b) Issue an immediate full refund of the total purchase amount of {price_val} directly to the consumer's bank account, along with interest at the rate of 18% per annum from the date of claim till realization;
   (c) AND pay a sum of ₹10,000/- (Rupees Ten Thousand Only) towards compensation for mental agony, harassment, and loss of productivity.

5. DEFAULT & PROCEEDINGS BEFORE CONSUMER COMMISSION (E-DAAKHIL):
   PLEASE TAKE CAREFUL NOTICE that should you fail or neglect to comply with this notice within the stipulated 15-day period, I shall be constrained to initiate formal statutory proceedings against you before the competent District Consumer Disputes Redressal Commission via the online e-Daakhil portal (Section 35) and register an official complaint with the National Consumer Helpline (NCH 1915), holding you jointly and severally liable for all consequential damages, litigation costs, and penal consequences.

Yours faithfully,

{consumer_name}
(Complainant / Consumer)
Enclosures:
1. Copy of Tax Invoice / Purchase Receipt (Ref: {inv_num})
2. Service Job Sheet / Warranty Card / Written Communication Records
================================================================================"""

    # NCH 1915 INGRAM Complaint Draft
    nch_grievance_draft = f"""NATIONAL CONSUMER HELPLINE (NCH 1915 / INGRAM) GRIEVANCE COMPLAINT:
--------------------------------------------------------------------------------
Complainant Name: {consumer_name}
Contact: {consumer_phone}
Opposite Party (Brand): {brand}
Opposite Party (Seller): {retailer}
Product / Service: {product_name}
Transaction / Invoice Date: {purchase_date_str}
Total Amount: {price_val}
Invoice / Order ID: {inv_num}
Grievance Category: Defective Goods / Warranty Repudiation / Deficiency in Service

Grievance Summary:
Purchased {product_name} on {purchase_date_str} for {price_val} via {retailer}. Product suffered functional defect: {issue_desc}. Warranty claim was improperly denied/delayed by {brand}. Formal 15-day demand notice (Ref: {notice_ref}) served. Seeking immediate replacement or full refund with compensation."""

    edaakhil_guidance = {
        "step_1": "Visit e-Daakhil portal (edaakhil.nic.in) and register/login using Aadhaar or Mobile OTP.",
        "step_2": "Select your local District Consumer Commission (District where you reside or where the purchase was made).",
        "step_3": "Upload: (1) Complaint Petition using this draft, (2) Purchase Invoice, (3) Service Center communication, (4) Copy of this 15-Day Legal Notice with postal/email receipt.",
        "step_4": "Pay zero court fees for consumer claims up to ₹5 Lakhs (Nil fee under Consumer Protection Act 2019).",
    }

    portal_links = {
        "edaakhil_url": "https://edaakhil.nic.in/",
        "nch_helpline_url": "https://consumerhelpline.gov.in/",
        "nch_toll_free_number": "1915",
        "nch_whatsapp_sms": "8800001915",
    }

    return LegalNoticeResponse(
        purchase_id=purchase.id,
        product_name=product_name,
        brand=purchase.brand,
        retailer=purchase.retailer,
        purchase_date=purchase_date_str,
        invoice_number=inv_num,
        amount_paid=price_val,
        notice_reference=notice_ref,
        legal_notice_text=legal_notice_text,
        nch_grievance_draft=nch_grievance_draft,
        statutory_sections_cited=statutory_sections,
        edaakhil_guidance=edaakhil_guidance,
        portal_links=portal_links,
    )
