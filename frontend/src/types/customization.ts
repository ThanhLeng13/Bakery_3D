export type ZoneData = { color?: string; decoration?: string; toppings?: string[] };

export interface CustomizationJson {
  size?: string;
  flavor?: string;
  cream_type?: string;
  cream_color?: string;
  topping_type?: string[];
  special_notes?: string;
  zones?: { top?: ZoneData; body?: ZoneData; border?: ZoneData };
}
