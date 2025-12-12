export enum SlideType {
  TITLE = 'TITLE',
  GRID_CARDS = 'GRID_CARDS',
  FLOWCHART = 'FLOWCHART',
  CODE_SPLIT = 'CODE_SPLIT',
  TERMINAL = 'TERMINAL',
  UI_SCREENSHOT = 'UI_SCREENSHOT',
  OUTRO = 'OUTRO'
}

export interface SlideData {
  id: number;
  type: SlideType;
  title?: string;
  subtitle?: string;
  content?: any;
  code?: string;
  image?: string;
}

export interface CardData {
  title: string;
  description: string;
  icon?: string;
  highlight?: boolean;
}

export interface FlowStep {
  label: string;
  role: string;
  icon: string;
  description?: string;
}