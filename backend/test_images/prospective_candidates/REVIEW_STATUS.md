# Prospective query candidates — NOT accepted test data

Collection performed after freezing `prospective_clip_protocol.json`.
18 candidates downloaded; all `label_verified=false`. No CLIP inference run.
Missing queries: candidate 06 (durian crepe; no accepted download), candidate 14
(tree; Commons returned HTTP 429 after bounded retries).

## Preliminary visual inspection via image tool / vision relay

- candidate_00: chocolate brownie with chocolate sauce on a white plate;
  consistent with broad brownie category. Not human-approved.
- candidate_01: Portuguese custard tarts in a bakery display with large sign;
  consistent with broad egg-tart category, but text is a confound. Not human-approved.

Do not mark these records human-verified on the strength of this note.

A later attempt to view candidate_02 through candidate_05 returned only
`Image omitted: exceeds maximum limit of 4 images per request`; it supplied no
visual evidence, so no label was approved. Open `review_candidates.html` locally
to inspect all 18 images. It is read-only and does not persist decisions.
Record filename, correct/incorrect/uncertain, actual class and reason before
editing any verification flags.

## Retrieval warnings requiring review/replacement BEFORE inference

Source titles raise label concerns (title alone is not final image review):
- candidate_02: Cream Puff Pavilion (may be a building rather than pastry).
- candidate_04: Burnt Basque Ube Cheese (variant may not match catalogue label).
- candidate_05: Croissant red velvet cheesecake (mixed dessert).
- candidate_07: military birthday pageant (not reliable banana-cake query).
- candidate_08: cassava cake (not reliable coconut custard-cake label).
- candidate_15: tomato returned for apple.
- candidate_18: portrait of Alexei Leonov returned for wristwatch.
- candidate_19: school returned for automobile.

The remaining candidates have not been visually reviewed. Their filenames and
metadata do NOT establish class correctness. Source/license metadata was obtained
from Commons API and byte hashes compared against old manifest; this does not
prove independence from every catalogue embedding image.

## Old dataset concern discovered during review

Old `ngoai_mien_banh/kem__1.jpg` contains both a fruit crumble and ice cream,
according to image-tool inspection. It is not a clean ice-cream-only negative.
Old `che__1.jpg` depicts rice pudding in bowls, consistent with non-cake dessert.
Do not silently relabel old measured reports. Existing threshold results remain
historical/exploratory, with possible label noise. A truly reviewed new set is
required for confirmation.
