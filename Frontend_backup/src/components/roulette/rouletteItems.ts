export type RouletteItem = {
  label: string;
  probability: string;
  popcornGain: number;
  expGain: number;
};

export const rouletteItems: RouletteItem[] = [
  { label: "🍿", probability: "50%", popcornGain: 3, expGain: 15 },
  { label: "🌭", probability: "25%", popcornGain: 6, expGain: 20 },
  { label: "🥤", probability: "15%", popcornGain: 10, expGain: 30 },
  { label: "🦑", probability: "9%", popcornGain: 15, expGain: 50 },
  { label: "🍗", probability: "1%", popcornGain: 20, expGain: 100 },
];
