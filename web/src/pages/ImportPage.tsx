import { useEffect } from 'react';
import { Link } from 'react-router-dom';

import { CsvImportWorkflow } from '../imports/CsvImportWorkflow';

export function ImportPage() {
  useEffect(() => {
    document.title = 'Import CSV | LifeLenz';
  }, []);

  return (
    <div className="import-page">
      <header className="page-intro">
        <p className="eyebrow">Records · CSV import</p>
        <h1>Import wellness records</h1>
        <p>
          Validate a versioned CSV, review the server report, and explicitly
          import only eligible unique rows.
        </p>
        <Link className="text-link" to="/app/records">
          Back to Records
        </Link>
      </header>
      <CsvImportWorkflow />
    </div>
  );
}
