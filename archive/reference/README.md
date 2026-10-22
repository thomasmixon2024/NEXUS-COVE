# Reference data

`geology.csv` is the only reference file the Geology Analyzer reads. It starts with a header row and no entries, so the tool stays silent until you add rows. Every value must come from a source you cite. Columns:

- `material`: the name an agent will see in a message, e.g. `granite`
- `property`: e.g. `compressive strength`
- `value` and `unit`: e.g. `170` and `MPa`
- `source`: where the number came from

The tool only reports rows whose material is named in the message. It never fills gaps.
