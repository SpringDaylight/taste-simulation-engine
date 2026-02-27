import { useMemo, useRef, useState, type CSSProperties } from "react";
import "./roulette.css";
import type { RouletteItem } from "./rouletteItems";

type Props = {
  items: RouletteItem[];
  onResult?: (item: RouletteItem) => void;
  onSpin?: () => Promise<RouletteItem | null> | RouletteItem | null;
  onResultConfirm?: (item: RouletteItem) => void;
};

export default function Roulette({ items, onResult, onSpin, onResultConfirm }: Props) {
  const [rotation, setRotation] = useState(0);
  const [isSpinning, setIsSpinning] = useState(false);
  const [resultOpen, setResultOpen] = useState(false);
  const [resultItem, setResultItem] = useState<RouletteItem | null>(null);
  const frameRef = useRef<number | null>(null);
  const startRef = useRef(0);
  const fromRef = useRef(0);
  const toRef = useRef(0);
  const rotationRef = useRef(0);
  const resultIndexRef = useRef(-1);
  const forcedResultRef = useRef<RouletteItem | null>(null);

  const segmentAngle = items.length ? 360 / items.length : 0;
  const startOffset = -segmentAngle / 2;
  const gradientOffset = ((startOffset % 360) + 360) % 360;
  const colors = ["#ffffff"];
  const easeOutCubic = (value: number) => 1 - Math.pow(1 - value, 3);

  const segments = useMemo(() => {
    if (!items.length) return [];
    return items.map((item, index) => {
      const start = startOffset + segmentAngle * index;
      const end = start + segmentAngle;
      const center = start + segmentAngle / 2;
      return { item, start, end, center, color: colors[index % colors.length] };
    });
  }, [items, segmentAngle, startOffset]);

  const getIndexFromRotation = (value: number) => {
    if (!segmentAngle) return 0;
    const normalized = ((value % 360) + 360) % 360;
    const pointerAngle = (360 - normalized) % 360;
    const index =
      Math.floor((pointerAngle + segmentAngle / 2) / segmentAngle) % items.length;
    return index;
  };

  const getForwardSnappedRotation = (value: number, index: number) => {
    if (!segmentAngle) return value;
    const normalized = ((value % 360) + 360) % 360;
    const centerAngle = index * segmentAngle;
    const desiredNormalized = (360 - centerAngle + 360) % 360;
    const diff = (desiredNormalized - normalized + 360) % 360;
    return value + diff;
  };

  const wheelStyle = useMemo(() => {
    if (!segments.length) {
      return { transform: `rotate(${rotation}deg)` };
    }
    const stops = segments
      .map((segment) => {
        const baseStart = segment.start - startOffset;
        const baseEnd = baseStart + segmentAngle;
        return `${segment.color} ${baseStart}deg ${baseEnd}deg`;
      })
      .join(", ");
    return {
      backgroundImage: `conic-gradient(from ${gradientOffset}deg, ${stops})`,
      transform: `rotate(${rotation}deg)`,
    };
  }, [segments, rotation, segmentAngle, startOffset, gradientOffset]);

  const selectResultIndex = () => {
    const rawWeights = items.map((item) => {
      const value = Number(item.probability.replace(/[^\d.]/g, "").trim());
      return Number.isFinite(value) ? value : 0;
    });
    const total = rawWeights.reduce((sum, value) => sum + value, 0);
    if (total <= 0) {
      return Math.floor(Math.random() * items.length);
    }
    const pick = Math.random() * total;
    let cursor = 0;
    for (let index = 0; index < rawWeights.length; index += 1) {
      cursor += rawWeights[index];
      if (pick <= cursor) return index;
    }
    return rawWeights.length - 1;
  };

  const animate = (timestamp: number, duration: number) => {
    if (!startRef.current) startRef.current = timestamp;
    const elapsed = timestamp - startRef.current;
    const progress = duration > 0 ? Math.min(elapsed / duration, 1) : 1;
    const eased = easeOutCubic(progress);
    const nextRotation =
      fromRef.current + (toRef.current - fromRef.current) * eased;
    rotationRef.current = nextRotation;
    setRotation(nextRotation);

    if (progress < 1) {
      frameRef.current = requestAnimationFrame((time) =>
        animate(time, duration)
      );
      return;
    }

    setIsSpinning(false);
    startRef.current = 0;
    frameRef.current = null;
    const index =
      resultIndexRef.current >= 0
        ? resultIndexRef.current
        : getIndexFromRotation(rotationRef.current);
    resultIndexRef.current = -1;
    const result = forcedResultRef.current ?? items[index];
    forcedResultRef.current = null;
    if (result) {
      setResultItem(result);
      setResultOpen(true);
      onResult?.(result);
    }
  };

  const closeResult = () => {
    if (resultItem) {
      onResultConfirm?.(resultItem);
    }
    setResultOpen(false);
    setResultItem(null);
  };

  const startSpin = async () => {
    if (isSpinning || !items.length) return;
    setResultOpen(false);
    setResultItem(null);
    if (frameRef.current) cancelAnimationFrame(frameRef.current);
    setIsSpinning(true);

    let index = selectResultIndex();
    let forcedItem: RouletteItem | null = null;

    if (onSpin) {
      try {
        const serverItem = await onSpin();
        if (!serverItem) {
          setIsSpinning(false);
          return;
        }
        const serverIndex = items.findIndex(
          (item) => item.label === serverItem.label
        );
        if (serverIndex >= 0) {
          index = serverIndex;
          forcedItem = serverItem;
        }
      } catch (error) {
        console.error("Failed to spin roulette:", error);
        setIsSpinning(false);
        return;
      }
    }

    forcedResultRef.current = forcedItem;
    resultIndexRef.current = index;
    fromRef.current = rotationRef.current;
    const extraRotations = 4 + Math.floor(Math.random() * 2);
    const snapped = getForwardSnappedRotation(rotationRef.current, index);
    toRef.current = snapped + extraRotations * 360;
    startRef.current = 0;
    const duration = 2200 + extraRotations * 300;
    frameRef.current = requestAnimationFrame((time) => animate(time, duration));
  };

  return (
    <div className="rm-roulette">
      <div className="rm-tooltip">
        <button
          className="rm-tooltip-btn"
          type="button"
          aria-label="확률표 보기"
        >
          ?
        </button>
        <div className="rm-tooltip-panel">
          <div className="rm-table">
            <div className="rm-table-header">
              <span>항목</span>
              <span>팝콘 수</span>
              <span>경험치 수</span>
            </div>
            {items.map((item) => (
              <div className="rm-row" key={item.label}>
                <span className="rm-label">{item.label}</span>
                <span className="rm-probability">{item.popcornGain}</span>
                <span className="rm-probability">{item.expGain}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
      <div className="rm-stage">
        <div className="rm-wheel-wrap">
          <div className="rm-pointer" />
          <div className="rm-wheel" style={wheelStyle}>
            <div className="rm-separators">
              {items.map((_, index) => (
                <span
                  className="rm-separator"
                  key={`sep-${index}`}
                  style={
                    {
                      transform: `rotate(${startOffset + index * segmentAngle - 90}deg)`,
                    } as CSSProperties
                  }
                />
              ))}
            </div>
            <ul className="rm-labels">
              {segments.map((segment) => (
                <li
                  key={segment.item.label}
                  style={
                    { "--angle": `${segment.center}deg` } as CSSProperties
                  }
                >
                  {segment.item.label}
                </li>
              ))}
            </ul>
            <div className="rm-center" />
          </div>
        </div>
      </div>

      <div className="rm-controls">
        <button
          className="primary-btn"
          type="button"
          onClick={startSpin}
          disabled={isSpinning}
        >
          룰렛 돌리기
        </button>
      </div>

      {resultOpen && resultItem && (
        <div
          className="modal"
          role="dialog"
          aria-modal="true"
          aria-labelledby="roulette-result-title"
        >
          <div
            className="modal-overlay"
            onClick={closeResult}
          />
          <div className="modal-content settings-modal rm-result-modal">
            <div className="modal-scroll">
              <div className="modal-header">
                <h2 id="roulette-result-title">획득 결과</h2>
                <button
                  className="icon-btn"
                  type="button"
                  aria-label="결과 닫기"
                  onClick={closeResult}
                >
                  ✕
                </button>
              </div>
              <div className="modal-section">
                <div className="rm-result-body">
                  <p className="rm-result-label">{resultItem.label}</p>
                  <p className="rm-result-popcorn">
                    팝콘 +{resultItem.popcornGain}
                  </p>
                  <p className="rm-result-exp">EXP +{resultItem.expGain}</p>
                </div>
              </div>
              <div className="modal-footer">
                <button
                  className="primary-btn"
                  type="button"
                  onClick={closeResult}
                >
                  확인
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
