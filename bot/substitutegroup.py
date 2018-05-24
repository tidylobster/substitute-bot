# Support functions for substitute groups
# ----------

def substitute_groups(message, groups, draft=False):
    final_message = ""
    last = []
    overfit = False
    word = ""
    for ch in message:
        if ch.isalpha():
            word += ch
        elif len(word) > 0:
            final_message, is_tail = update_final_message(ch, final_message, groups, last, word, draft)
            if is_tail and not overfit:
                overfit = is_tail

            word = ""
        else:
            final_message += ch
            word = ""

    if len(word) > 0:
        final_message, is_tail = update_final_message("", final_message, groups, last, word, draft)
        if is_tail and not overfit:
            overfit = is_tail

    if overfit and draft:
        final_message += " (...)"

    if not draft:
        final_message += "\n" + ' '.join(last)

    return final_message


# Removing @ from group name
def clear_group_name(group_name):
    return group_name.replace("@", "")

# This shit is not working. Help me >_>
def get_translitted(str, case_insansitive = True):
    return  str
    # tranlitted = translit(str, draft=True)
    # if case_insansitive:
    #     tranlitted = tranlitted.lower()
    #
    # return tranlitted

def update_final_message(ch, final_message, groups, last, word, draft):
    overfit = False
    gr = find_group(groups, word)
    if gr != None:
        group_string = get_group_members_string(gr, draft)
        if len(gr.members) > 4:
            last.append(group_string)
            final_message += word
            overfit = True
        else:
            final_message += group_string
    else:
        final_message += word
    final_message += ch
    return final_message, overfit


def find_group(groups, word):
    group_tr = get_translitted(word, False)
    gr = None
    for item in groups:
        name_cleared = clear_group_name(item.name)
        if name_cleared == group_tr:
            gr = item
            continue
    return gr


# I'm not sure, but maybe highlighting group name is here.
def get_group_members_string(group, draft):
    if len(group.members) == 0:
        return group.name

    return '{}({})'.format(group.name, '...' if draft else ' '.join(list(map(lambda x: x.alias, group.members))))
