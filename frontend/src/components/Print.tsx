/** The signature object: a pin as a print on a cotton mat, with its wall label. */

import { imageUrl, type Pin } from "../lib/api";

export function Print({
  pin,
  selected,
  onSelect,
  priority = false,
}: {
  pin: Pin;
  selected?: boolean;
  onSelect?: (pin: Pin) => void;
  /** The first print in a hang is the LCP element: load it eagerly. */
  priority?: boolean;
}) {
  const heroes = pin.items.filter((i) => i.is_hero);
  const named = heroes.length ? heroes : pin.items;

  return (
    <button
      type="button"
      className="print"
      aria-pressed={selected ?? false}
      onClick={() => onSelect?.(pin)}
    >
      <span className="print__mat">
        <span className="print__window">
          <img
            className="pin-image"
            src={imageUrl(pin.image_file)}
            alt={pin.title ? `Saved image: ${pin.title}` : "Saved image"}
            loading={priority ? "eager" : "lazy"}
            fetchPriority={priority ? "high" : undefined}
            width={600}
            height={800}
          />
        </span>
      </span>

      <span className="label">
        <span className="label__name">{pin.title || "Untitled"}</span>
        <br />
        <span className="label__meta">
          {pin.analyzed_at
            ? named.length
              ? named.slice(0, 3).map((i) => i.name).join(", ")
              : "Nothing to shop in this one"
            : "Not read yet"}
        </span>
      </span>

      {pin.analyzed_at && pin.items.length > 0 && (
        <span className="pencil">
          _____ / {pin.items.length} {pin.items.length === 1 ? "piece" : "pieces"}
        </span>
      )}
    </button>
  );
}
