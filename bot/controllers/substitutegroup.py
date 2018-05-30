from transliterate import translit
from transliterate.exceptions import LanguageDetectionError
from telegram.utils.helpers import escape_markdown


# Support functions for substitute groups
# ---------------------------------------


def substitute_groups(message, groups, draft=False):
    final_message = ""
    last = []
    overfit = False
    word = ""
    for ch in message:
        if ch.isalpha():
            word += ch
        elif len(word) > 0:
            final_message, is_tail = update_final_message(final_message, groups, last, word, draft)
            if is_tail and not overfit:
                overfit = is_tail

            final_message += ch
            word = ""
        else:
            final_message += ch
            word = ""

    if len(word) > 0:
        final_message, is_tail = update_final_message(final_message, groups, last, word, draft)
        if is_tail and not overfit:
            overfit = is_tail

    if overfit and draft:
        final_message += " (...)"

    if not draft and len(last) > 0:
        final_message += "\n\n" + ' '.join(last)

    return final_message


def get_translitted(message, case_insansitive=True):
    try:
        translitted = translit(message, reversed=True)
    except LanguageDetectionError:
        translitted = message

    if case_insansitive:
        translitted = translitted.lower()
    return translitted


def update_final_message(final_message, groups, last, word, draft):
    overfit = False
    gr = find_group(groups, word)

    if gr is not None:
        clear_bold_group = group_bold_text(word)
        group_string = get_group_members_string(gr, draft)
        if len(gr.members) > 4:
            last.append(group_string)
            final_message += clear_bold_group
            overfit = True
        else:
            final_message += group_string
    else:
        final_message += word

    return final_message, overfit


def find_group(groups, word: str):
    group_tr = get_translitted(word, False)
    gr = None
    for item in groups:
        if item.name == group_tr:
            gr = item
            break
    return gr


def get_group_members_string(group, draft: bool = False):
    name_group = group_bold_text(group.name)
    if len(group.members) == 0:
        return name_group
    return '{} ({})'.format(name_group, '...' if draft else escape_markdown(' '.join(map(lambda x: x.alias, group.members))))


def group_bold_text(name):
    return f'*{name}*'
