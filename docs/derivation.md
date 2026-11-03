# Derivation

## 1. VGM (SOLAS chapter VI, regulation 2)

A packed container cannot be loaded without a verified gross mass. Method 2 adds the parts:

    gross mass = cargo + packing and securing material + container tare

The check recomputes the sum from the VGM fields and accepts the declared figure when

    |declared - (cargo + packing + tare)| <= tolerance x (cargo + packing + tare)

The tolerance is set by each national authority, not by SOLAS; 5% is used here and lives in
`rules.json`. Hand case (tested): 20,000 + 400 + 2,200 = 22,600 kg, 5% is 1,130 kg, so
23,730 kg passes and 23,731 kg fails. A second rule refuses a gross mass above the maximum
for the size type (30,480 kg for a 22G1, 32,500 kg for a 45G1, assumed plate values).

## 2. B/L weight

The B/L shows cargo gross weight, without the tare. So per container the draft weight must
match cargo + packing from the VGM, within the same tolerance, and the HS lines must add up
to the container total exactly.

## 3. ISO 6346 check digit

Letters take values from A = 10 upward, skipping 11, 22 and 33 (so K = 21, U = 32,
V = 34). Digits keep their value. Position i (0 to 9) is weighted 2^i:

    check = (sum of value x 2^i) mod 11, then mod 10

Hand case (tested), CSQU305438:

    C13 x1 + S30 x2 + Q28 x4 + U32 x8 + 3 x16 + 0 x32 + 5 x64 + 4 x128 + 3 x256 + 8 x512
    = 13 + 60 + 112 + 256 + 48 + 0 + 320 + 512 + 768 + 4096 = 6185
    6185 mod 11 = 3, so the full number is CSQU3054383.

One wrong serial digit changes the sum by (difference) x 2^i, never a multiple of 11, so the
remainder always changes. The final mod 10 writes a remainder of 10 as 0, so a typo that
moves the remainder between 0 and 10 still slips through. The check digit catches most
typos, not all.

## 4. Other cross-field rules

- Container set: the numbers on the VGMs and on the draft must be the same set, and their
  count must equal the booked quantity.
- Consignee: equal after upper-casing and removing punctuation and extra spaces.
- Packages: containers on the draft add up to the booked packages; HS lines add up to the
  containers.
- HS lines: 6 to 10 digits, and the first four digits are a heading declared at booking.

## 5. Ranking

Each rule belongs to one document. Draft rules are due at the SI cut-off, VGM rules at the
VGM cut-off. Mismatches are sorted by cut-off, nearest first, then by severity (3 blocks
loading, 2 changes the B/L, 1 is a clerical difference). A cut-off already missed goes to
the end: the box is already rolled or the B/L must be amended, so working on it first does
not save anything.

## 6. Measurement

600 synthetic bookings arrive over 25 days. Each of seven error types is injected
independently with probability 3% per booking (`synthetic.py`). Six are typing errors in one
document. The seventh, "truth", is a wrong consignee copied into every document; no
consistency rule can see it. One analyst fixes 3 bookings a day with the shipper. A fix on
day t clears every mismatch whose cut-off is after day t. After the cut-off, an open draft
error costs one B/L amendment and an open VGM error rolls the booking to the next vessel.
Assumed costs: 450.00 per amendment, 2,000.00 per rollover.
