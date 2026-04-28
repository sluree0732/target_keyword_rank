import json

import google.generativeai as genai


def extract_keywords_batch(
    titles: list,
    grade: int,
    count: int,
    api_key: str,
) -> dict:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash-lite')

    titles_text = '\n'.join(f'{i + 1}. {t}' for i, t in enumerate(titles))
    prompt = (
        f'아래 {len(titles)}개의 블로그 제목에서 각각 키워드를 추출해줘.\n'
        f'세부키워드 등급(1)에서 대표키워드 등급(5)를 1부터 5까지 '
        f'등급을 나눈다고 했을 때 등급 [{grade}]으로 각 제목당 [{count}]개씩 뽑아줘.\n\n'
        f'제목 목록:\n{titles_text}\n\n'
        f'JSON 형식으로만 출력해. title 필드에는 위 제목 목록의 원본 제목을 그대로 사용해:\n'
        f'{{"results": [{{"title": "원본제목", "keywords": ["키워드A", "키워드B"]}}]}}'
    )

    response = model.generate_content(
        prompt,
        generation_config={'response_mime_type': 'application/json'},
    )

    data = json.loads(response.text)
    results_list = data.get('results', [])

    mapping = {}
    for i, item in enumerate(results_list):
        if i < len(titles):
            mapping[titles[i]] = item.get('keywords', [])
    return mapping
