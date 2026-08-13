export function NotesField({
  value,
  disabled,
  onChange,
}: {
  value: string;
  disabled: boolean;
  onChange(value: string): void;
}) {
  return (
    <div className="field">
      <label htmlFor="record-notes">Notes (optional)</label>
      <textarea
        id="record-notes"
        name="record-notes"
        rows={3}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        disabled={disabled}
        aria-describedby="record-notes-hint"
      />
      <span className="field__hint" id="record-notes-hint">
        Add only context you are comfortable storing with this record.
      </span>
    </div>
  );
}
