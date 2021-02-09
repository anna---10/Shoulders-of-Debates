from os.path import abspath, dirname
import csv
from pathlib import Path
import sys
PARENT_DIR = dirname(dirname(abspath(__file__)))
sys.path.append(PARENT_DIR)
sys.path.append(str(Path(PARENT_DIR + '/scripts')))
import preprocess_general as pp


path_data = PARENT_DIR + '/data/essay/'

def get_posts_and_args_from_BIO_sentences_csv(sentences, arg_ID_offset = -1):
    
    posts = []
    arguments = []
    topic_ID = 0
    arg_ID = arg_ID_offset
    argument = ''
    post = []
    for s in sentences:
        if s[0] != str(topic_ID):
            posts.append({'ID': topic_ID,'post' : post}) # append post to posts
            topic_ID = int(s[0]) #reset topic ID
            post = []
        if s[1] == 'B': #beginning
            arguments.append({
                'ID': arg_ID,
                'premise' : argument,
                'claim' : '',
                'stance': None
                }) #append argument to arguments
            argument = '' #reset argument

            arg_ID += 1 #set new arg ID
            argument = s[2] #initialize argument
            post.append((arg_ID, s[2])) #append sentence to post
        elif s[1] == 'I':
            argument = argument + ' ' + s[2] #append argument
            post.append((arg_ID, s[2])) #append sentence to post
        else: # outside ('O')
            post.append((None, s[2])) #append sentence to post
    arguments.append({
                'ID': arg_ID,
                'premise' : argument,
                'claim' : '',
                'stance': None
                })
    posts.append({'ID': topic_ID,'post' : post})

    return (arguments[1:], posts, arg_ID)

def get_json_from_BIO_csv(path_data, bio_prefix = 'essay_', topic_prefix = 'topics_', suffix = 'train', arg_ID_offset = -1):
    sentences = pp.load_csv_into_list_of_lists(path_data, bio_prefix + suffix)
    topics = pp.load_csv_into_list_of_lists(path_data, topic_prefix + suffix)

    arguments, posts, arg_ID = get_posts_and_args_from_BIO_sentences_csv(sentences, arg_ID_offset=arg_ID_offset)
    dict_list = []
    outer_d = dict()
    for p in posts:
        outer_d = dict()
        outer_d['ID'] = p['ID']
        outer_d['topic'] = topics[p['ID']][1]
        outer_d['subtopics'] = []
        inner_d = dict()
        inner_d['ID'] = p['ID']
        inner_d['title'] = topics[p['ID']][1]
        arg_IDs = list(set([sentence[0] for sentence in p['post']]))
        inner_d['arguments'] = [a for a in arguments if a['ID'] in arg_IDs]
        inner_d['posts'] = [p]
        outer_d['subtopics'].append(inner_d)
        dict_list.append(outer_d)
    return (dict_list, arg_ID)

def change_IDs(offset, list_dict):
    new_list_dict = []
    for item in list_dict:
        item['ID'] = item['ID'] + offset
        item['subtopics'][0]['ID'] = item['ID']
        item['subtopics'][0]['posts'][0]['ID'] = item['ID']
        new_list_dict.append(item)
    return new_list_dict

train, arg_ID_offset = get_json_from_BIO_csv(path_data, suffix='train')
val, arg_ID_offset = get_json_from_BIO_csv(path_data, suffix='val', arg_ID_offset = arg_ID_offset)
test, _ = get_json_from_BIO_csv(path_data, suffix='test', arg_ID_offset = arg_ID_offset)

#Change duplicate indexes with adding offset
val = change_IDs(len(train), val)
test = change_IDs(len(train) + len(val), test)

pp.write_dict_to_json(path_data, 'train', train)
pp.write_dict_to_json(path_data, 'val', val)
pp.write_dict_to_json(path_data, 'test', test)


