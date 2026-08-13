import type { WellnessRecord } from '../api/types';
import { presentRecord } from './recordPresentation';

export function RecentRecords({ records }: { records: WellnessRecord[] }) {
  if (!records.length) {
    return (
      <div className="records-empty">
        <h3>No wellness records yet</h3>
        <p>
          Start with one of the record types above. Your recorded data will
          begin to shape your wellness summary.
        </p>
      </div>
    );
  }

  // The API returns chronological order. Keep that deterministic order while
  // limiting presentation to its ten newest records; this is not pagination.
  const recentRecords = records.slice(-10);
  return (
    <ol className="recent-records">
      {recentRecords.map((record) => {
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
  );
}
