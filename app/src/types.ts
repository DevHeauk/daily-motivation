export type Quote = {
  id: string;
  topic: string;
  text: string;
  author: string;
};

export type DailyQuote = Quote & {
  date: string;
};

export type ViewSource = 'today' | 'swipe';
