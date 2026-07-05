## 1. Cascade Hard-Deletion & Danger Zone (Completed)

- [x] 1.1 Add `delete_assignments()` to `TaxonomyRepository` and `AnnotationDefinitionRepository`
- [x] 1.2 Update taxonomy and annotation service layers to support cascading hard-delete when `force=True`
- [x] 1.3 Add `/assignments/count` endpoints and `?force=true` query parameters to controllers
- [x] 1.4 Exclude and filter out archived taxonomies/definitions during trade and check-in schema serialization
- [x] 1.5 Add count fetch helpers and hook up the force parameter inside frontend delete mutations
- [x] 1.6 Build the frontend red Danger Zone confirmation box with name-typing validation
- [x] 1.7 Remove redundant "Manage Tags" and "Manage Annotations" settings links from QualitativeMetadataPanel

## 2. Metadata Archiving, Unarchiving, & Library Filtering (Pending)

- [x] 2.1 Expose explicit "Archive" and "Unarchive" buttons in tag and metric Details Views
- [x] 2.2 Add "Show Archived" toggle switch in TaxonomyManager list grid to filter out archived tags by default
- [x] 2.3 Add "Show Archived" toggle switch in AnnotationManager list grid to filter out archived metrics by default
- [x] 2.4 Verify toggle and unarchive flows under Next.js and ensure perfect visual consistency
