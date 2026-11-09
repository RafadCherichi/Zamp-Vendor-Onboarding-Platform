import type { ApplicationDraftUpdate } from '../../types/application';

export interface DemoAutofillProfile {
  id: string;
  name: string;
  description: string;
  draft: ApplicationDraftUpdate;
  documents: Record<string, string>;
}

// Demo data is tied to the seeded demo vendor's own company. Never offer a
// different supplier identity from an authenticated vendor's application.
export const DEMO_AUTOFILL_PROFILES: DemoAutofillProfile[] = [
  {
    id: 'apex-components',
    name: 'Apex Components & Fasteners',
    description: 'A sample profile and proof set for this demo vendor account.',
    draft: {
      legal_name: 'Apex Components & Fasteners',
      trade_name: 'Apex Fasteners',
      constitution: 'PROPRIETORSHIP',
      date_of_establishment: '2018-04-12',
      registered_address: 'Plot 42, Wagle Industrial Estate, Road No. 16',
      operating_address: 'Plot 42, Wagle Industrial Estate, Road No. 16',
      city: 'Thane',
      state: 'Maharashtra',
      pincode: '400604',
      pan: 'AAPFU0938L',
      is_gst_registered: false,
      is_udyam_registered: true,
      udyam_number: 'UDYAM-MH-02-0012345',
      contact_name: 'Vikram Malhotra',
      contact_designation: 'Proprietor',
      contact_email: 'vendor@apexcomponents.com',
      contact_mobile: '+91 98765 43210',
      authorised_signatory_name: 'Vikram Malhotra',
      bank_account_holder_name: 'Apex Components & Fasteners',
      bank_account_number: '9876543210123',
      bank_ifsc: 'HDFC0000123',
      bank_account_type: 'CURRENT',
      bank_name: 'HDFC Bank',
      categories: ['manufacturer'],
      declaration_accurate_info: false,
      declaration_authorised_rep: false,
      declaration_verification_consent: false,
    },
    documents: {
      PAN_PROOF: 'synthetic_pan_card.pdf',
      BANK_PROOF: 'synthetic_cancelled_cheque.pdf',
      CONSTITUTION_PROOF: 'synthetic_udyam_certificate.pdf',
      UDYAM_CERTIFICATE: 'synthetic_udyam_certificate.pdf',
    },
  },
];

export function getDemoAutofillProfilesForVendor(legalName: string): DemoAutofillProfile[] {
  return DEMO_AUTOFILL_PROFILES.filter((profile) => profile.draft.legal_name === legalName);
}
