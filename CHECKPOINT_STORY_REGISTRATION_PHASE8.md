# CHECKPOINT — Story Registration Phase 8

## Status
Phase 8 hoàn tất về mặt implementation.

## Quyết định
Thêm một lớp `StoryRegistrationStore` per-user để ánh xạ:

`user_id + source_url -> story_id`

Lớp này chỉ là registration/index. Không chứa chapter content, không thay thế Manifest hoặc Story State.

## Flow
URL mới:
`register -> Adapter Resolution -> build_index -> Manifest + Registration -> StoryEngine.initialize`

URL đã đăng ký:
`register -> Registration lookup -> Story State + Manifest -> không re-index`

## Ownership
- Registration: user + source URL -> story_id
- Manifest: story/chapter index
- Story State: runtime position/status/hash
- 0neStory.epub: chapter content
- 0neStoryTOC.epub: navigation

## Tests
- per-user/source isolation
- existing registration is immutable
