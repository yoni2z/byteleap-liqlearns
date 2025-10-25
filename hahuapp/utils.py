import random
from .models import (
    WordAudio,
    LetterFillIn, 
    SentencePunctuation,
    WordVideo, 
    SentenceSynonym,
    LetterSound,
    AmharicLetterFamily,
    ParagraphCreation,
    AmharicLetterAudio
)

### ---------------- The Centralized Mapping -------------------


def get_letter_fill_question():
    words_data = LetterFillIn.objects.all()
    selected_word = random.choice(words_data)
    return {
        'type': 'letter_fill',
        'question': selected_word.display_word,
        'choices': selected_word.choices,
        'correct_answer': selected_word.correct_letter,
        'extra_info': selected_word.meaning,
    }


def get_photo_to_word_question():
    question = WordAudio.objects.filter(image__isnull=False).order_by('?').first()
    incorrect_choices = WordAudio.objects.exclude(id=question.id).order_by('?')[:3]
    choices = list(incorrect_choices) + [question]
    random.shuffle(choices)
    return {
        'type': 'photo_to_word',
        'question': question.image.url,
        'choices': [choice.word for choice in choices],
        'correct_answer': question.word,
        'extra_info': question.definition,
    }


def get_word_to_photo_question():
    question = WordAudio.objects.order_by('?').first()
    incorrect_choices = WordAudio.objects.exclude(id=question.id).order_by('?')[:3]
    choices = list(incorrect_choices) + [question]
    random.shuffle(choices)
    return {
        'type': 'word_to_photo',
        'question': question.word,
        'choices': [choice.image.url for choice in choices],
        'correct_answer': question.image.url,
        'extra_info': question.definition,
    }


def get_video_to_word_question():
    question = WordVideo.objects.order_by('?').first()
    incorrect_choices = WordVideo.objects.exclude(id=question.id).order_by('?')[:3]
    choices = list(incorrect_choices) + [question]
    random.shuffle(choices)
    return {
        'type': 'video_to_word',
        'question': question.video_file.url,
        'choices': [choice.word for choice in choices],
        'correct_answer': question.word,
        'extra_info': question.hint,
    }


def get_sentence_synonym_question():
    question = SentenceSynonym.objects.order_by('?').first()
    distractors = list(SentenceSynonym.objects.exclude(id=question.id).values_list('correct_word', flat=True).order_by('?')[:3])
    choices = distractors + [question.correct_word]
    random.shuffle(choices)
    return {
        'type': 'sentence_synonym',
        'question': question.sentence,
        'choices': choices,
        'correct_answer': question.correct_word,
        'extra_info': question.hint,
    }


def get_sentence_punctuation_question():
    sentence = SentencePunctuation.objects.order_by('?').first()
    choices = sentence.choices.split(",")
    random.shuffle(choices)
    return {
        'type': 'sentence_punctuation',
        'question': sentence.text,
        'choices': choices,
        'correct_answer': sentence.correct_answer,
        'extra_info': sentence.correct_text,
    }


def get_letter_sound_charades_question():
    sounds = LetterSound.objects.all()
    selected_sound = random.choice(sounds)
    correct_letter = selected_sound.letter
    other_sounds = LetterSound.objects.exclude(letter=correct_letter)
    incorrect_choices = random.sample(list(other_sounds), 3)
    choices = [correct_letter] + [sound.letter for sound in incorrect_choices]
    random.shuffle(choices)
    return {
        'type': 'letter_sound_charades',
        'question': selected_sound.sound_field.url,
        'choices': choices,
        'correct_answer': correct_letter,
        'extra_info': selected_sound.letter or "",
    }


def get_word_sound_identification_question():
    all_words = WordAudio.objects.all()
    selected_word = random.choice(all_words)
    correct_word = selected_word.word
    other_words = WordAudio.objects.exclude(word=correct_word)
    incorrect_choices = random.sample(list(other_words), 3)
    choices = [correct_word] + [word.word for word in incorrect_choices]
    random.shuffle(choices)
    return {
        'type': 'word_sound_identification',
        'question': selected_word.audio_file.url,
        'choices': choices,
        'correct_answer': correct_word,
        'extra_info': selected_word.definition or "",
    }


def get_listen_and_identify_question():
    all_sounds = WordAudio.objects.all()
    selected_sound = random.choice(all_sounds)
    correct_audio = selected_sound
    other_sounds = WordAudio.objects.exclude(word=correct_audio.word)
    incorrect_choices = random.sample(list(other_sounds), 3)
    choices = [correct_audio] + incorrect_choices
    random.shuffle(choices)
    return {
        'type': 'listen_and_identify',
        'question': correct_audio.audio_file.url,
        'choices': [choice.word for choice in choices],
        'correct_answer': correct_audio.word,
        'extra_info': selected_sound.definition or "",
    }

### ----------- list of questions ---------------

def get_random_questions():
    question_fetchers = [
        get_letter_fill_question,
        get_photo_to_word_question,
        get_word_to_photo_question,
        get_video_to_word_question,
        get_sentence_synonym_question,
        get_sentence_punctuation_question,
        get_letter_sound_charades_question,
        get_word_sound_identification_question,
        get_listen_and_identify_question,
    ]

    questions = []
    while len(questions) < 10:
        fetcher = random.choice(question_fetchers)
        question = fetcher()
        if question not in questions:  # Avoid duplicates
            questions.append(question)

    return questions
