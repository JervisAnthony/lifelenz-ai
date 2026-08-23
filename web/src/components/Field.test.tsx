import { render, screen } from '@testing-library/react';

import { Field } from './Field';

describe('Field', () => {
  it('keeps labels associated when the same requested id is mounted twice', () => {
    render(
      <>
        <Field id="hydration-volume" label="Manual volume" />
        <Field id="hydration-volume" label="Correction volume" />
      </>,
    );

    const manual = screen.getByLabelText('Manual volume');
    const correction = screen.getByLabelText('Correction volume');

    expect(manual.id).toMatch(/^hydration-volume-/);
    expect(correction.id).toMatch(/^hydration-volume-/);
    expect(manual.id).not.toBe(correction.id);
  });
});
