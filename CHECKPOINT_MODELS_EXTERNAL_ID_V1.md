# CHECKPOINT — Universal Chapter Model V1

The image-assets model is preserved and extended with `Chapter.external_id`.

- `Chapter.number`: Tàng Thư's sequential chapter position used by Engine.
- `Chapter.external_id`: native platform identifier, e.g. Wattpad part ID `402782528`.
- Existing `ChapterAsset` and `ChapterContent` remain intact.
- Existing state serialization/migration remains intact.

This fixes compatibility between the image-assets implementation and the
Wattpad ID model.
