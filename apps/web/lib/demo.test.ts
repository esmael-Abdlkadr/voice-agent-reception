import { describe, expect, it } from "vitest";
import { outcomeLabel } from "./presentation";

describe("outcomeLabel", () => {
  it("turns stored outcome keys into readable labels", () => {
    expect(outcomeLabel("appointment_booked")).toBe("appointment booked");
  });

  it("keeps voicemail labels customer-facing", () => {
    expect(outcomeLabel("voicemail_simulated")).toBe("voicemail");
  });
});
