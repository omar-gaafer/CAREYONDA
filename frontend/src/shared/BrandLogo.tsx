const base = `${import.meta.env.BASE_URL}brand/`;
const fullLogo = `${base}careyonda-logo-transparent.png`;
const iconLogo = `${base}careyonda-icon-transparent.png`;

/** Original brand artwork on a neutral surface; no color filters or cropping. */
export function BrandLogo({
  variant = "full",
  compact = false,
}: {
  variant?: "full" | "icon" | "navigation";
  compact?: boolean;
}) {
  const icon = variant === "icon" || (variant === "navigation" && compact);
  return (
    <picture className={`brand-logo brand-logo--${variant}`}>
      {variant === "navigation" && (
        <source
          media="(max-width: 700px)"
          srcSet={fullLogo}
          width={1236}
          height={696}
        />
      )}
      <img
        src={icon ? iconLogo : fullLogo}
        alt={icon ? "CAREYONDA mission emblem" : "CAREYONDA logo and wordmark"}
        width={icon ? 625 : 1236}
        height={icon ? 496 : 696}
        decoding="async"
      />
    </picture>
  );
}
