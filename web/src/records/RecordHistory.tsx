import type { WellnessRecord } from '../api/types';
import { presentRecord } from './recordPresentation';

export function RecordHistory({ records }: { records: WellnessRecord[] }) {
  if (!records.length) {
    return (
      <div className="records-empty">
        <h3>No records match these filters</h3>
        <p>Adjust the record type or date range to review another part of your history.</p>
      </div>
    );
  }

  const newestFirst = [...records].reverse();
  return (
    <>
      <p className="summary-source" role="status">
        {records.length.toLocaleString()} {records.length === 1 ? 'record' : 'records'} found
      </p>
      <ol className="recent-records" aria-label="Filtered wellness record history">
        {newestFirst.map((record) => {
          const presentation = presentRecord(record);
          return (
            <li key={record.metadata.record_id}>
              <div>
                <h3>{presentation.label}</h3>
                <p>{presentation.summary}</p>
              </div>
              <time dateTime={record.metadata.recorded_at}>
                {presentation.timestamp}
              </time>
            </li>
          );
        })}
      </ol>
    </>
  );
}
