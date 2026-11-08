import type { Application, DocumentSlot } from '../types/application';

export function isAcceptedAlternative(slot: DocumentSlot, constitution: Application['constitution']): boolean {
  return constitution === 'PROPRIETORSHIP'
    && slot.document_type === 'CONSTITUTION_PROOF'
    && slot.detected_document_type === 'UDYAM_CERTIFICATE';
}

export function hasWrongDocumentType(slot: DocumentSlot, constitution: Application['constitution']): boolean {
  return slot.is_type_match === false
    && Boolean(slot.detected_document_type)
    && slot.detected_document_type !== 'UNKNOWN'
    && !isAcceptedAlternative(slot, constitution);
}
