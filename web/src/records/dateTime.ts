const DATE_TIME_LOCAL_PATTERN =
  /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?$/;

function parsedLocalDateTime(value: string): Date {
  const match = DATE_TIME_LOCAL_PATTERN.exec(value);
  if (!match) {
    throw new Error('Enter a complete local date and time.');
  }
  const [, year, month, day, hour, minute, second = '00'] = match;
  const date = new Date(
    Number(year),
    Number(month) - 1,
    Number(day),
    Number(hour),
    Number(minute),
    Number(second),
  );
  if (
    date.getFullYear() !== Number(year) ||
    date.getMonth() !== Number(month) - 1 ||
    date.getDate() !== Number(day) ||
    date.getHours() !== Number(hour) ||
    date.getMinutes() !== Number(minute) ||
    date.getSeconds() !== Number(second)
  ) {
    throw new Error('Enter a valid local date and time.');
  }
  return date;
}

export function localDateTimeToAwareIso(
  value: string,
  offsetMinutes?: number,
): string {
  const localDate = parsedLocalDateTime(value);
  const browserOffset = offsetMinutes ?? localDate.getTimezoneOffset();
  if (!Number.isInteger(browserOffset) || Math.abs(browserOffset) > 14 * 60) {
    throw new Error('The local time zone offset is unavailable.');
  }
  const sign = browserOffset <= 0 ? '+' : '-';
  const absoluteOffset = Math.abs(browserOffset);
  const hours = String(Math.floor(absoluteOffset / 60)).padStart(2, '0');
  const minutes = String(absoluteOffset % 60).padStart(2, '0');
  const normalized = value.length === 16 ? `${value}:00` : value;
  return `${normalized}${sign}${hours}:${minutes}`;
}

export function currentLocalDateTime(date = new Date()): string {
  const part = (value: number) => String(value).padStart(2, '0');
  return `${date.getFullYear()}-${part(date.getMonth() + 1)}-${part(date.getDate())}T${part(date.getHours())}:${part(date.getMinutes())}`;
}

export function elapsedMinutes(start: string, end: string): number {
  const startDate = parsedLocalDateTime(start);
  const endDate = parsedLocalDateTime(end);
  return (endDate.getTime() - startDate.getTime()) / 60_000;
}
