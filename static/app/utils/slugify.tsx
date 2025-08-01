/**
 * Transforms the given string to a slugified version. (e.g. "My Project" => "my-project")
 *
 * Allows only lowercase alphanumeric values, hyphens, and underscores (should match backend validation rules).
 * Normalizes special characters to a-z where applicable (accents, ligatures, etc).
 * Converts spaces to hyphens.
 */
export default function slugify(str: string): string {
  return str
    .normalize('NFKD') // Converts accents/ligatures/etc to latin alphabet
    .toLowerCase()
    .replace(/[^a-z0-9_\s-]/g, '') // Remove all invalid characters
    .replace(/[-\s]+/g, '-'); // Replace multiple spaces or hyphens with a single hyphen
}
