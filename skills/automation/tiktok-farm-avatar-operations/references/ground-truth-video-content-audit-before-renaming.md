# Ground-Truth Video Content Audit Before Profile Renaming & Bio Writing

## 1. Context & The "Hallucinated Sub-Niche" Trap
In TikTok Farm Profile Standardization (quy trình 4-in-1: Avatar, Tên, Bio, Hashtag), an agent often checks the Excel sheet (`tik3.xlsx`, `tik5.xlsx`) to see the high-level category (e.g. `Âm nhạc`, `Làm đẹp`, `Gái xinh`) and looks at the username handle (e.g. `@angthanhkhoa5528`).

**The Failure Mode:**
- The agent takes the keyword `Âm nhạc` and the name `khoa`, and **hallucinates a specific sub-niche** (e.g. *"Hát & Đàn Keyboard / Piano"*).
- It generates a name: `Thanh Khoa Piano` and writes a bio: *"Chia sẻ giai điệu piano và niềm đam mê âm nhạc mỗi ngày."*
- It applies the change directly to the live account via ADB without ever verifying what videos are actually posted on the profile.
- **The Reality:** The account actually posted comedy sketches, lifestyle vlogs, and beauty videos with `#lamdepvietnam #lamdep #tiktokvietnam #fyp`. There was zero musical content.
- **The Severe Consequence:** TikTok enforces a strict **7-day Display Name Cooldown (`NAME_CHANGE_COOLDOWN_7D`)**. Once renamed to `Thanh Khoa Piano`, the account is locked with a completely mismatched identity for an entire week, damaging feed distribution and account reputation.

---

## 2. Invariant: Ground-Truth Video Inspection Before Renaming

### Step 1: Pre-Renaming Video Grid Inspection
Before formulating or applying a new Nickname / Display Name:
1. **Inspect Video Thumbnails:** Check the grid of posted videos on the profile screen (via OCR / Vision).
2. **Open at least 1 Published Video:** Tap the top-viewed or latest video to inspect:
   - Video visual scene (is it playing an instrument? coding on screen? dancing? talking comedy?).
   - Video Caption & Hashtags (OCR the bottom text area).
   - Audio Title (check whether it's original audio, trending sound, or voiceover).

### Step 2: Cross-Check Against Excel Category
| Video Evidence (Ground Truth) | Excel Keyword | Action Required |
|---|---|---|
| Matches Excel (e.g. Piano keys visible, hashtags `#piano #music`) | `Âm nhạc` | Proceed with specific sub-niche (Name: `Thanh Khoa Piano`). |
| Contradicts Excel (e.g. Comedy sketches, hashtags `#lamdep #haihuoc`) | `Âm nhạc` (Stale / Desynced) | **Ground-Truth Wins:** Align Name & Bio with the *actual video content* (e.g. `Thanh Khoa Vlog` / `Thanh Khoa Daily`), OR update Excel category. NEVER force an imaginary sub-niche onto conflicting videos. |
| Account has 0 videos posted | Any | Fall back to Excel niche, but keep Name broad and canonical (e.g. Real Vietnamese full name without narrow instrument suffixes). |

### Step 3: Name Safety & Reversibility Hierarchy
- **Bio is Soft (Reversible immediately):** Bio can be changed multiple times without cooldown. If a mistake is made, rewrite it immediately via `AdbKeyboard`.
- **Nickname is Hard (Irreversible for 7 days):**
  - Always prefer broad, natural Vietnamese names (Họ + Tên đệm + Tên thật, e.g. `Đặng Nhật Huy`, `Nguyễn Thanh Khoa`) over hyperspecific keyword names (e.g. `Thanh Khoa Piano`), unless the channel's video content is 100% verified to be dedicated to that specific instrument.
  - Adding niche suffixes (`Piano`, `Dev`, `Vlog`) is strictly forbidden unless backed by positive visual proof in the published video grid.

---

## 3. Checklist Before Submitting Name Change
- [ ] Have I viewed at least 1 actual video frame or thumbnail?
- [ ] Do the hashtags on the top video match the proposed name's niche?
- [ ] Is the proposed name a clean, accented Vietnamese name?
- [ ] If the name has a niche suffix, is there unequivocal proof on-screen?
- [ ] Has the Positive Contract Verifier (`verify_profile_positive.py`) been configured with verified expected fields?
