# Checkpoint — Story Manifest Store Phase 1

## Chốt

- Manifest là cache navigation/index, không phải runtime state.
- Mỗi `user_id + story_id` có một manifest riêng.
- Manifest chỉ lưu story metadata và chapter metadata/link.
- Không lưu chapter content.
- Không lưu `content_hash`, `status`, hoặc `target_chapter_number`.
- `StoryStateStore` vẫn giữ runtime state hiện tại.
- Phase 1 chỉ thêm `StoryManifestStore`; chưa sửa `StoryApplication`/`StoryEngine`.

## Bước kế tiếp

Tích hợp `StoryManifestStore` vào `StoryApplication` để lần đầu mới `build_index()`, các lần sau load manifest; sau đó mới xử lý tail refresh và one-chapter delivery trên cache.
