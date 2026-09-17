"""
Pure UI building blocks. Save persists per-user via local_client.save_
bookmark() once someone's signed in (local_auth.current_user()), falling
back to session-only save for a logged-out/guest view --- see that
function's docstring for the full per-user-vs-session split.
"""
import streamlit as st

import local_auth
from local_client import save_bookmark, record_resource_opened

FILE_TYPE_STYLE = {
    "video": {"color": "#DC2626", "label": "VIDEO", "icon": "▶️"},  # red, per request --- notes/docs already get their own distinct color below; video gets red the same way
    "ppt":  {"color": "#F97316", "label": "PPT",  "icon": "📊"},
    "pdf":  {"color": "#EF4444", "label": "PDF",  "icon": "📄"},
    "note": {"color": "#3B82F6", "label": "NOTE", "icon": "📝"},
    "doc":  {"color": "#3B82F6", "label": "DOC",  "icon": "📃"},
}
DEFAULT_STYLE = {"color": "#6B7280", "label": "FILE", "icon": "📎"}


def inject_base_css():
    st.markdown(
        """
        <style>
        div[data-testid="stAppViewContainer"] > .main { padding-bottom: 5.5rem; }
        .card {
            border: 1px solid #E5E7EB;
            border-radius: 12px;
            padding: 0.9rem 1rem;
            margin-bottom: 0.6rem;
            background: #FFFFFF;
        }
        .card-title { font-weight: 600; font-size: 0.98rem; margin-bottom: 0.15rem; }
        .card-meta { color: #6B7280; font-size: 0.8rem; }
        .type-chip {
            display: inline-block;
            font-size: 0.7rem;
            font-weight: 700;
            padding: 0.1rem 0.5rem;
            border-radius: 6px;
            color: white;
            margin-right: 0.4rem;
        }
        .course-chip {
            display: inline-block;
            border: 1px solid #E85D2C;
            color: #E85D2C;
            border-radius: 999px;
            padding: 0.3rem 0.9rem;
            margin-right: 0.5rem;
            font-weight: 600;
            font-size: 0.85rem;
        }
        .switch-wordmark {
            font-weight: 800;
            letter-spacing: -0.02em;
            color: #E85D2C;
        }
        .switch-wordmark .dot { color: #1A1A2E; }
        .st-key-bottom_nav {
            position: fixed;
            bottom: 0; left: 0; right: 0;
            background: #FFFFFF;
            border-top: 1px solid #E5E7EB;
            padding: 0.4rem 0.5rem;
            z-index: 999;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def wordmark(size: str = "1.4rem"):
    """Renders the 'switch.' wordmark --- lowercase, bold, trailing dot in ink not orange."""
    st.markdown(
        f'<div class="switch-wordmark" style="font-size:{size};">switch<span class="dot">.</span></div>',
        unsafe_allow_html=True,
    )


def file_type_chip(file_type: str) -> str:
    style = FILE_TYPE_STYLE.get(file_type, DEFAULT_STYLE)
    return f'<span class="type-chip" style="background:{style["color"]}">{style["icon"]} {style["label"]}</span>'


def resource_card(resource: dict, key_prefix: str):
    """Renders one feed/list card. Returns the button-click routing signal, if any."""
    style = FILE_TYPE_STYLE.get(resource.get("file_type"), DEFAULT_STYLE)
    with st.container():
        st.markdown(
            f"""
            <div class="card" style="border-left: 4px solid {style['color']};">
                <div>{file_type_chip(resource.get('file_type', ''))}
                    <span class="card-meta">{resource.get('course_code', '')}</span>
                </div>
                <div class="card-title">{resource.get('title', 'Untitled')}</div>
                <div class="card-meta">
                    {resource.get('uploader', '')}{' · ' if resource.get('uploader') else ''}{resource.get('uploaded_at', '')}
                    {' · ▲ ' + str(resource['upvotes']) if 'upvotes' in resource else ''}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        cols = st.columns([1, 1, 1])
        open_clicked = cols[0].button("Open", key=f"{key_prefix}_open_{resource['id']}", use_container_width=True)
        save_clicked = cols[1].button("🔖 Save", key=f"{key_prefix}_save_{resource['id']}", use_container_width=True)
        share_clicked = cols[2].button("🔗 Share", key=f"{key_prefix}_share_{resource['id']}", use_container_width=True)

        if open_clicked:
            st.session_state["active_resource_id"] = resource["id"]
            st.session_state["_last_opened_resource"] = resource
            st.switch_page("pages/6_Viewer.py")
        if save_clicked:
            user = local_auth.current_user()
            save_bookmark(resource, student_id=user["user_id"] if user else "demo-student")
            st.toast(f"Saved \"{resource.get('title')}\"")
        if share_clicked:
            st.toast("Share link copied (placeholder --- wire to real deep-link generation later)")


def youtube_embed(video_id: str, height: int = 220):
    """Renders an actual playable YouTube iframe embed (not just a link
    or a thumbnail-with-click-through) --- this is the literal 'embed
    the videos' ask. Wrapped in a rounded container matching .card's
    styling so it sits visually consistent with the rest of the UI
    rather than looking like a bare unstyled iframe."""
    st.markdown(
        f"""
        <div style="border-radius:12px; overflow:hidden; border:1px solid #E5E7EB;">
            <iframe width="100%" height="{height}"
                src="https://www.youtube.com/embed/{video_id}"
                title="YouTube video player"
                frameborder="0"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowfullscreen>
            </iframe>
        </div>
        """,
        unsafe_allow_html=True,
    )


def drive_doc_embed(embed_url: str, height: int = 400):
    """Round 3: renders a Google Docs/Sheets/Slides/Drive-file inline
    preview via an iframe pointed at Google's own /preview (or /embed,
    for Slides) address --- the note/doc (drive_notes/drive_questions)
    equivalent of youtube_embed() above, same wrapping/styling
    treatment. `embed_url` is the already-built address from
    tree_store.drive_embed_url(); this function only renders it,
    matching youtube_embed()'s own split between building the address
    (tree_store) and rendering it (here).

    Google's /preview endpoint renders its own "you need access" page
    inside the iframe for a document that isn't shared "Anyone with
    the link" --- there's no way to tell that apart from a real
    document loading correctly from here, since the iframe's contents
    are cross-origin. That's why the Viewer (pages/6_Viewer.py) always
    shows a direct Open-in-Google-Docs link alongside this embed, not
    only when this is judged to have failed."""
    st.markdown(
        f"""
        <div style="border-radius:12px; overflow:hidden; border:1px solid #E5E7EB;">
            <iframe src="{embed_url}" width="100%" height="{height}" frameborder="0"></iframe>
        </div>
        """,
        unsafe_allow_html=True,
    )


def video_resource_card(resource: dict, key_prefix: str):
    """Like resource_card(), but for file_type == 'video': renders the
    actual playable embed inline (via youtube_embed()) instead of an
    Open button that navigates away, since the point of embedding is
    not having to leave the card to watch. Save/Share stay as buttons
    below the embed --- Open is dropped since there's nothing further
    for a click-through 'Open' to do once the video is already playing
    right there."""
    style = FILE_TYPE_STYLE.get("video", DEFAULT_STYLE)
    video_id = resource.get("youtube_video_id")
    with st.container():
        st.markdown(
            f"""
            <div class="card" style="border-left: 4px solid {style['color']}; padding-bottom:0.5rem;">
                <div>{file_type_chip('video')}
                    <span class="card-meta">{resource.get('course_code', '')}</span>
                </div>
                <div class="card-title">{resource.get('title', 'Untitled')}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if video_id:
            youtube_embed(video_id)
        else:
            # A youtube-kind link whose url didn't match the expected
            # pattern (see tree_store.youtube_video_id) --- fall back to
            # a plain link rather than an iframe pointed at nothing.
            st.caption(f"Couldn't embed this video. [Open on YouTube]({resource.get('url', '')})")

        cols = st.columns([1, 1])
        save_clicked = cols[0].button("🔖 Save", key=f"{key_prefix}_save_{resource['id']}", use_container_width=True)
        share_clicked = cols[1].button("🔗 Share", key=f"{key_prefix}_share_{resource['id']}", use_container_width=True)
        if save_clicked:
            user = local_auth.current_user()
            save_bookmark(resource, student_id=user["user_id"] if user else "demo-student")
            st.toast(f"Saved \"{resource.get('title')}\"")
        if share_clicked:
            st.toast("Share link copied (placeholder --- wire to real deep-link generation later)")

        # Recorded here (not just from the Viewer page) because embedded
        # videos are now watched in-place and may never route through
        # 6_Viewer.py at all --- history would silently miss every
        # embedded view otherwise. Guarded to fire once per Streamlit
        # session per resource: Streamlit reruns this whole page on ANY
        # button click anywhere on it (e.g. clicking Save on a
        # different card), and without this guard every such rerun
        # would re-record this video as "just opened" even though the
        # person didn't touch it that time --- reaching Course Detail
        # at all already required an explicit navigation click, so
        # that's the real "opened" signal; re-renders after that within
        # the same session aren't.
        if video_id:
            recorded_key = f"_history_recorded_{resource['id']}"
            if not st.session_state.get(recorded_key):
                user = local_auth.current_user()
                if user:
                    record_resource_opened(user["user_id"], resource)
                st.session_state[recorded_key] = True


def bottom_nav(active: str):
    """Renders the fixed bottom tab bar. `active` highlights the current tab.

    Round 3 fix: this used to open the wrapping div with one
    st.markdown() call, run st.columns()/st.button() in between, then
    close it with a second, separate st.markdown("</div>") call.
    Streamlit renders each st.markdown() call as its own self-contained
    element on the page --- nothing rendered between two separate calls
    actually ends up nested inside a div opened by an earlier one. In
    practice that meant the opening call produced an empty, self-closed
    box; the columns/buttons rendered afterward, outside it and
    unstyled by .bottom-nav's fixed-position/background/border rules;
    and the second call's closing tag was left dangling with nothing
    to close, its own orphaned element on the page.

    Fixed with st.container(key=...), which Streamlit (1.39+; see the
    requirements.txt bump) renders as a real wrapping element carrying
    an .st-key-<key> class --- so the columns/buttons below genuinely
    end up inside the styled container this time, in one call instead
    of two. See inject_base_css() above for the matching
    .st-key-bottom_nav rule (renamed from the old .bottom-nav, since
    the class is no longer applied by hand)."""
    with st.container(key="bottom_nav"):
        cols = st.columns(4)
        tabs = [
            ("Home", "🏠", "pages/1_Home.py"),
            ("My Courses", "📚", "pages/2_My_Courses.py"),
            ("Upload", "⬆️", "pages/4_Upload.py"),
            ("Saved", "🔖", "pages/5_Saved.py"),
        ]
        for col, (label, icon, page) in zip(cols, tabs):
            is_active = label == active
            display = f"**{icon} {label}**" if is_active else f"{icon} {label}"
            if col.button(display, key=f"nav_{label}", use_container_width=True):
                st.switch_page(page)


def course_unit_tile(course: dict, key_prefix: str, target_page: str = "pages/3_Course_Detail.py"):
    """A single course-unit tile for the 'My Active Courses' grid (gap #1/#2
    of the handoff doc's tile redesign). Uses the existing .card shell (same
    border/radius/shadow every other card in the app uses) with the
    .course-chip style --- defined in inject_base_css() from the original
    build but never actually applied anywhere before this --- as the pill
    around the course-unit name, so this reuses two pieces of styling that
    already existed rather than inventing a fourth distinct card look.
    Returns True if the tile's button was clicked this run (caller decides
    what to do with that, matching how resource_card() etc. hand click
    signals back rather than navigating internally in every case)."""
    with st.container():
        st.markdown(
            f"""
            <div class="card" style="text-align:center; padding:1.1rem 0.8rem;">
                <div><span class="course-chip">{course.get('code', 'COURSE')}</span></div>
                <div class="card-title" style="margin-top:0.5rem;">{course.get('name', 'Untitled')}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        clicked = st.button("Open", key=f"{key_prefix}_tile_{course['id']}", use_container_width=True)
    if clicked:
        st.session_state["active_course"] = course
        st.switch_page(target_page)
    return clicked
