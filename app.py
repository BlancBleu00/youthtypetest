import json
import os
import random
import re
from collections import Counter
import streamlit as st

AXIS_PAIRS = [("E", "I"), ("S", "N"), ("T", "F"), ("J", "P")]
TIEBREAK = {"E": "I", "S": "N", "T": "F", "J": "P"}  # 동점 기본값

def load_json(filename: str):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, filename)
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def choose_letter(scores, a, b, tie_pick):
    if scores[a] > scores[b]:
        return a
    if scores[b] > scores[a]:
        return b
    return tie_pick

def get_code(scores):
    code = ""
    for a, b in AXIS_PAIRS:
        code += choose_letter(scores, a, b, TIEBREAK.get(a, b))
    return code

def compute_scores(questions, answers):
    scores = Counter()
    for q in questions:
        qid = q["id"]
        pick = answers.get(qid)
        if pick is None:
            continue
        choice = q["choices"][pick]
        for k, v in choice["score"].items():
            scores[k] += v
    return scores

def current_question(questions):
    real_index = st.session_state.order[st.session_state.idx]
    return questions[real_index]

def reset_all(questions):
    st.session_state.order = list(range(len(questions)))
    random.shuffle(st.session_state.order)
    st.session_state.idx = 0
    st.session_state.answers = {}
    st.session_state.done = False
    st.session_state.just_auto_advanced = False
    st.rerun()

def go_next(questions):
    if st.session_state.idx < len(questions) - 1:
        st.session_state.idx += 1
        st.session_state.just_auto_advanced = True
    else:
        st.session_state.done = True

def go_prev():
    if st.session_state.idx > 0:
        st.session_state.idx -= 1
        st.session_state.just_auto_advanced = False

def extract_mbti_code(text: str):
    """
    "분위기 조율자, ESFJ" 같은 문자열에서 MBTI 코드(대문자 4글자)를 뽑아낸다.
    """
    if not text:
        return None
    m = re.search(r"\b([EINFS TJP]{4})\b", text.replace(" ", ""))
    return m.group(1) if m else None

def on_pick_change(questions, qid: str):
    # 중복 자동 이동 방지
    if st.session_state.get("just_auto_advanced", False):
        st.session_state.just_auto_advanced = False
        return

    pick_key = f"pick_{qid}"
    picked = st.session_state.get(pick_key, None)

    prev = st.session_state.answers.get(qid, None)
    if prev is None and picked in (0, 1):
        st.session_state.answers[qid] = picked
        go_next(questions)
        st.rerun()

    # 이미 선택했던 걸 바꿔도 자동 다음은 안 함(원하면 여기서 go_next 가능)
    if prev in (0, 1) and picked in (0, 1) and prev != picked:
        st.session_state.answers[qid] = picked


st.set_page_config(page_title="청년 유형 테스트", page_icon="🧩", layout="centered")
st.title("🧩 청년 유형 테스트")
st.caption("카드형 · 선택하면 자동으로 다음으로 넘어갑니다.")

questions = load_json("questions.json")
types = load_json("types.json")

# Session init
if "order" not in st.session_state:
    st.session_state.order = list(range(len(questions)))
    random.shuffle(st.session_state.order)

if "idx" not in st.session_state:
    st.session_state.idx = 0

if "answers" not in st.session_state:
    st.session_state.answers = {}

if "done" not in st.session_state:
    st.session_state.done = False

if "just_auto_advanced" not in st.session_state:
    st.session_state.just_auto_advanced = False

total = len(questions)
current = st.session_state.idx + 1
st.progress(current / total, text=f"{current} / {total}")

# DONE screen
if st.session_state.done:
    scores = compute_scores(questions, st.session_state.answers)
    code = get_code(scores)
    persona = types.get(code)

    st.success("✨ 결과가 나왔습니다!")

    if persona:
        st.markdown(f"## {persona['nickname']} ({code})")
        st.markdown(f"### “{persona['one_liner']}”")
        st.caption(f"{persona.get('group','')} · {persona.get('tag','')}")

        st.divider()
        st.subheader("🤝 나랑 잘 맞는 케미")
        st.caption("※ 재미 요소(밈). 정식 검사 결과로 받아들이진 말기.")

        best_str = persona.get("best_match", "")
        if best_str:
            st.markdown(f"**추천 케미:** {best_str}")

            # best_match 문자열에서 코드 추출해서 상세도 보여주기(있으면)
            bm_code = extract_mbti_code(best_str)
            if bm_code and bm_code in types:
                bm = types[bm_code]
                st.markdown(f"- {bm['nickname']} ({bm_code})")
                st.markdown(f"  - _{bm['one_liner']}_")
        else:
            st.write("추가 예정")

    else:
        st.markdown(f"## {code}")
        st.warning("types.json에 이 코드가 없습니다. (types.json 확인)")

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 다시하기", use_container_width=True):
            reset_all(questions)
    with col2:
        if persona:
            share_text = (
                f"청년 유형 테스트 결과: {persona['nickname']} ({code})\n"
                f"“{persona['one_liner']}”\n"
                f"{persona.get('group','')} · {persona.get('tag','')}\n"
                f"잘 맞는 케미: {persona.get('best_match','')}"
            )
        else:
            share_text = f"청년 유형 테스트 결과: {code}"

        st.download_button(
            "📋 결과 텍스트 저장",
            data=share_text,
            file_name="youth_type_result.txt",
            use_container_width=True
        )

    with st.expander("디버그(축 점수 보기)"):
        st.write({k: scores[k] for k in ["E","I","S","N","T","F","J","P"]})

    st.stop()

# CARD screen
q = current_question(questions)
qid = q["id"]

st.markdown(f"### {q['prompt']}")

# 이미지(있으면 출력)
img = q.get("image")
if img:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    img_path = os.path.join(base_dir, img)
    if os.path.exists(img_path):
        st.image(img_path, use_container_width=True)
    else:
        st.caption(f"(이미지 파일을 못 찾음: {img})")

choices = [q["choices"][0]["text"], q["choices"][1]["text"]]
existing = st.session_state.answers.get(qid, None)

st.radio(
    label="",
    options=[0, 1],
    format_func=lambda x: choices[x],
    index=existing if existing in (0, 1) else 0,
    key=f"pick_{qid}",
    label_visibility="collapsed",
    on_change=on_pick_change,
    args=(questions, qid),
)

# 선택값 저장
picked_now = st.session_state.get(f"pick_{qid}", 0)
st.session_state.answers[qid] = picked_now

st.divider()

left, mid, right = st.columns([1, 1, 1])
with left:
    st.button("⬅️ 이전", on_click=go_prev, use_container_width=True, disabled=(st.session_state.idx == 0))
with mid:
    if st.session_state.idx == total - 1:
        st.button("🎉 결과 보기", on_click=lambda: go_next(questions), use_container_width=True)
    else:
        st.button("➡️ 다음", on_click=lambda: go_next(questions), use_container_width=True)
with right:
    st.button("🔄 초기화", on_click=lambda: reset_all(questions), use_container_width=True)
