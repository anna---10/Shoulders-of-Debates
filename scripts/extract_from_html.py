import re
import os
import math
import pandas as pd
import json
import random
import csv
import sys
import nltk 
from os.path import abspath, dirname
PARENT_DIR = dirname(dirname(abspath(__file__)))
#"/vol3/anna/thesis-argument-mining-and-summarization"
sys.path.append(PARENT_DIR)
sys.path.append(str(Path(PARENT_DIR + '/scripts')))
import preprocess_general as pp
import html
from os.path import dirname, abspath

def pedia_find_topic(line):

    """ Checks the input string from a debatepedia html document for containing the topic of the dicussion

    Parameters
    ----------
    line: str
        one line of the html document to be checked whether it contains the topic

    Returns
    -------
    str
        The topic of the discussion or None if the line doesn't contain the topic
    """

    if re.search(r'</h1>', line):
        before = re.search(r'<h1 class="firstHeading">Debate: ', line)
        after = re.search(r'</h1>' ,line)
        topic = line[before.end():after.start()]
        return topic
    return None

def pedia_find_subtopic(line):
    
    """ Checks the input string from a debatepedia html document for containing a sub topic of the dicussion

    Parameters
    ----------
    line: str
        one line of the html document to be checked whether it contains a sub topic

    Returns
    -------
    str
        A sub topic of the discussion or None if the line doesn't contain a sub topic
    """
    
    if re.search(r'<h3>', line):
        before = re.search(r'<h3>', line)
        after = re.search(r'</h3>' ,line)
        line = line[before.end():after.start()].strip()
        #Exlude background and resources headings
        if not line.startswith(('Pro/','Background', 'Videos', 'YouTube', 'Pro and', 'Organizations pro', 'Argument', 'Summary', 'External')):
            return line
    return None

def pedia_find_argument(line, a_ID, stance = ''):
    
    """ Checks the input string from a debatepedia html document for containing an argument of the dicussion

    Parameters
    ----------
    line: str
        one line of the html document to be checked whether it contains an argument
    stance: str
        the stance of the current arguments

    Returns
    -------
    str
        An argument of the discussion or None if the line doesn't contain an argument
    """
    
    if re.search(r'<ul><li><b>', line): #argument starts with a bold claim after a bullet point
        #CLAIM
        before = re.search(r'<ul><li><b>(<a href[^<]+>)?', line) #optionally the claim is within a hyper ref
        after = re.search(r'(</a>)?</b>', line) #until the end of the bold section
        claim = line[before.end():after.start()]
        #PREMISE
        before = re.search(r'</b>(\s?(<a href[^<]+>[^<]+</a>)?(<i>)?[^<]*(</i>)?(:| - )"?)?', line)
        #before = re.search(r'</b>(\s?(<a href[^<]+>[^<]+</a>)?(<i>)?[\w \.\,\;\$\"\-\')(]*(</i>)?(:| - "))?', line)
        premise = line[before.end():] #only the next line closes with </li></ul>
        premise = re.sub(r'<a href[^<]+>[^<]+</a>', '', premise) #remove all links within the premise
        return ({'ID': a_ID, 'claim': claim.strip(), 'premise': premise.strip().strip('"').strip('“'), 'stance': stance}) #remove whitespaces and quotes at the end and beginning
    return None

def pedia_find_stance(line):
    
    """ Checks the input string from a debatepedia html document for containing a stance

    Usually pro/con or yes/no but also clinton, obama, republican, democrat, mccain, clinton is better and obama is better

    Parameters
    ----------
    line: str
        one line of the html document to be checked whether it contains a stance 

    Returns
    -------
    str
        A stance (usually pro/con or yes/no see above) or None
    """
    
    if re.search(r'<h4>', line):
        before = re.search(r'<h4>', line)
        after = re.search(r'</h4>', line)
        stance = line[before.end():after.start()].lower().strip() #usually pro/con or yes/no
        return stance
    return None

def org_find_url(line):
    
    """ Checks the input string from a debateorg warc document for containing a url of the dicussion
    
    Use only the first url found in this way since only this one is leading to the
    webpage of the discussion.

    Parameters
    ----------
    line: str
        one line of the warc document to be checked whether it contains a url

    Returns
    -------
    str
        A url or None if the line doesn't contain a url.
        The first url in every document found in this way is the url leading to the discussion's website
    """

    if line.startswith('WARC-Target-URI:'):
        before = re.search(r'WARC-Target-URI: ', line)
        url = line[before.end()+1:-1]
        return url
    return None

def org_find_title(line):
    
    """ Checks the input string from a debateorg html document for containing the title of the dicussion

    Parameters
    ----------
    line: str
        one line of the html document to be checked whether it contains the title

    Returns
    -------
    str
        The title of the discussion or None if the line doesn't contain the title
    """

    if re.search(r'<h1 class="top">([^<]+)</h1>', line):
        before = re.search(r'<h1 class="top">', line)
        after = re.search(r'</h1>' ,line)
        title = html.unescape(line[before.end():after.start()])
        return title
    return None

def org_find_category(line):
     
    """ Checks the input string from a debateorg html document for containing the category of the dicussion

    Parameters
    ----------
    line: str
        one line of the html document to be checked whether it contains the category

    Returns
    -------
    str
        The category of the discussion or None if the line doesn't contain the category
    """

    if re.search(r'Content Category', line):
        before = re.search(r'"Content Category", ', line)
        after = re.search(r'\);' ,line)
        category = line[before.end()+1:after.start()-1]
        return category
    return None

def remove_html_tags_keep_br(s):
       
    """ Removes all html tags in the input string apart from the <br /> tag

    Parameters
    ----------
    s: str
        input string

    Returns
    -------
    str
        The cleaned string with <br /> tag as only html tag
    """
    s = re.sub(r'<a href[^<]+>[^<]+</a>', ' ', s) #remove all links within the string
    s_list = s.split('<br />')
    s_list = [re.sub('<([^<]+)>', ' ', e) for e in s_list] #remove all other html tags
    s = '<br />'.join(s_list)
    return s

def org_find_posts(line, posts = [], post='', within=False, stance=''):
     
    """ Checks the input line from a debateorg html document whether it is part of a post
    
    Dependent on the input parameters (=state variables) the final list of posts is built
    line by line. For each new document the function should be called with post = [],
    within = False and post = '' and then for each line with the returned values of the previous call.

    Parameters
    ----------
    line: str
        one line of the html document to be checked whether it is part of a post
    posts: list of str
        the list of posts up to the current line (default is the empty list)
    post: str
        the current post up to the current line
    within: bool
        whether the line before was part of a post (default is False)

    Returns
    -------
    (list, str, bool, str)
        The state variables (posts, post, within) to be used for the next call
    """

    #Post starts
    if line in ['<p class="pos0">Con</p>', '<p class="pos1">Pro</p>']:
        within = True
        post = ''
        if line == '<p class="pos0">Con</p>':
            stance = 'con'
        else: stance = 'pro'
        return (posts, post, within, stance)
    #Post ends
    if within and (re.search(r'<(div|td) class', line)):
        after = re.search(r'<(div|td) class', line)
        line = line[:after.start()]
        line = remove_html_tags_keep_br(line)
        within = False
        post = post + line
        post = post.lstrip(' ')
        if len(post) >=1:
            posts.append({'post': html.unescape(post), 'stance' : stance}) #remove &amp and &quot
        return(posts, post, within, stance)
    #Within a post
    if within:
        line = remove_html_tags_keep_br(line)
        post = post + line
    return (posts, post, within, stance)
    
    
def create_dict_debatepedia(path_html):
      
    """ Creates a list of dictionaries representing the discussions in debatepedia

    Parameters
    ----------
    path_html: str
        the path to the directory which contains the documents each holding one discussion

    Returns
    -------
    list of dict
        The list of discussions, each being a dict with the shape:
         {'ID': topic ID
         'topic': discussion title, 
         'subtopics': [{'ID': subtopic ID
                        'title': sub heading,
                        'arguments':[{'ID': argument ID
                                      'claim': claim,
                                      'premise': premise,
                                      'stance': pro/con}]
                        'posts':[{
                                'ID': post ID
                                'post' : [(argID, sentence)]
                                }] 
                        }]
        }
        
        The topic is the title of the discussion, the subtopics are the sub headings 
        worded as questions (or often Frame:question) and the arguments are the single
        bullet points under each sub heading with the claim in bold print and the premise
        the text after the referece to the source (separated by colon or dash).
        The posts are generated from the arguments.
    """

    discussions = [] #list of all discussions = topics
    t_ID = 0
    s_ID = 0
    a_ID = 0
    for file in os.listdir(path_html):
        with open(path_html + file, encoding='utf8') as f:
            subtopics = []
            arguments = [] 
            topic = ''
            subtopic = ''
            stance = ''
            
            for line in f: #go through every line in file
                line = line.rstrip()
                #TOPIC 
                if pedia_find_topic(line):
                    topic = pedia_find_topic(line)
                #HEADLINE
                if pedia_find_subtopic(line):
                    if subtopic != '':
                        subtopics.append({'ID': s_ID, 'title' : subtopic, 
                            'arguments': arguments, 'posts': generate_posts_from_arguments(arguments, s_ID)}) #"old" subtopic and list of arguments
                        s_ID+=1
                    subtopic = pedia_find_subtopic(line) #current subtopic
                    arguments = [] #new list that will contain the arguments of the current subtopic
                if pedia_find_stance(line):
                    stance = pedia_find_stance(line)
                #ARGUMENTS
                if pedia_find_argument(line, stance):
                    arguments.append(pedia_find_argument(line, a_ID, stance))
                    a_ID+=1
            discussions.append({'ID': t_ID, 'topic': topic, 'subtopics': subtopics})
            t_ID+=1
    return discussions


def create_dict_debateorg(path_html):
     
    """ Creates a list of dictionaries representing the discussions in debateorg

    Parameters
    ----------
    path_html: str
        the path to the directory which contains the documents each holding one discussion

    Returns
    -------
    list of dict
        The list of discussions, each being a dict with the shape:
        {'ID': subtopic ID
         'title': discussion title,
         'category': category,
         'url': url,
         'posts': ['post': text,
                   'stance': pro/con]
        }
    """
    
    discussions = []
    ID = 0
    #TODO IDs for arguments??
    for file in os.listdir(path_html):
        with open(path_html+ file, encoding='utf8') as f:
            posts = []
            urls = []
            title = ''
            category = ''
            post = ''
            stance = ''
            within = False #whether a post has started
            for line in f:
                line = line.rstrip()
                #URL reference
                if org_find_url(line):
                    urls.append(org_find_url(line))
                #TITLE
                if org_find_title(line):
                    title = org_find_title(line)
                #CATEGORY  
                if org_find_category(line):
                    category = org_find_category(line)
                #POSTS
                posts, post, within, stance = org_find_posts(line, posts, post, within, stance)
            discussions.append({'ID': ID, 'title': title, 'category': category, 'url':urls[0],'posts': posts})
            ID += 1
    return discussions



def split_sentences(text):
    
    """ Split a text into sentences
    
    Additionally to nltk.sent_tokenize functionality, split on <br /> tags

    Parameters
    ----------
    text: str
        the input text to be split into sentences
    
    Returns
    -------
    list of str
        list of sentences: contains empty strings for new lines
    
    """

    paragraphs  = text.split('<br />')
    sent_lst = []
    for p in paragraphs:
        if len(p) > 0:
            sent_lst.append('') 
            sent_lst = sent_lst + nltk.sent_tokenize(p) #concatenate empty sentence and sentences found by nltk
    return sent_lst[1:]


def generate_posts_from_arguments(arguments, sID):

    """ Creates post from arguments on random basis
    
    With maximum 9 (number chosen randomly) arguments within a post and maximum 6 (number chosen randomly) posts per subtitle. 
    Only the premises are taken as arguments (claims are ignored).
    Empty lines are also inserted between arguments on a random basis.

    Parameters
    ----------
    arguments: list of dict
        List of dictionaries of shape 
        [{ 'ID': argumentID,
        'claim': claim,
        'premise': premise,
        'stance': pro/con}]
    sID: int
        subtopic ID

    Returns
    -------
    posts: list of dict
        List of dictionaries of shape
        [{'ID': post ID
          'post' : [(argID, sentence)]
        }] 
                       
    """
    if len(arguments) == 0:
        return []

    args_tuples = [(a['ID'], a['premise']) for a in arguments]
    #TODO not random
    nr_posts = random.randint(1, max(6, len(args_tuples)))
    list_of_arglists = []

    #CREATE RANDOM LIST OF ARGUMENT LISTS
    for pID in range(0, nr_posts):
        nr_args = random.randint(1, min(9, len(arguments))) #maximum 9 arguments within a post
        #TODO range from 0, binomial
        nr_empty = random.randint(1, nr_args) #number of empty lines to insert randomly
        args_tuples_selection = random.sample(args_tuples, k=nr_args) #because of random.sample no repetitions of arguments here
        
        #Insert empty lines between argument on random basis
        for i in (range(0, nr_empty)): 
            pos = random.choice(range(0, nr_args + i)) #random position of emtpy lines between arguments
            args_tuples_selection.insert(pos, (None, ''))
        list_of_arglists.append({'ID' : str(sID) + '-' + str(pID), 'post': args_tuples_selection}) 
    
    #SPLIT ARGUMENTS INTO SENTENCES AND KEEP THE ARGUMENT IDs
    result = [] #posts is a list of dictionaries of shape {'ID': p['ID'], 'post' : [(argID, sentence)]}
    for arglist in list_of_arglists:
        sentences = [] #join the sentences of the arguments into one list
        for a in arglist['post']:
            if a[1] == '':
                sentences.append(a) #empty line, no label
            else:
                sentences = sentences + [(a[0], s) for s in split_sentences(a[1])]
        result.append({'ID': arglist['ID'], 'post' : sentences})
    return result

#TODO Change to relative path and/or move the data
path_html = "C:/Users/AnnaS/data/Debatten/html/"

d = dirname(dirname(abspath(__file__)))
path_data = d + "/data/"

# pedia_discussions = create_dict_debatepedia(path_html + "debatepedia/")
# length = len(pedia_discussions)
# random.seed(24)
# random.shuffle(pedia_discussions)
# test = pedia_discussions[:math.floor(0.15*length)]
# rest = pedia_discussions[math.floor(0.15*length):]
# train = rest[:math.floor(0.85*len(rest))]
# val = rest[math.floor(0.85*len(rest)):]

# pp.write_dict_to_json(path_data+ 'debatepedia/', 'train', train)
# pp.write_dict_to_json(path_data+ 'debatepedia/', 'val', val)
# pp.write_dict_to_json(path_data+ 'debatepedia/', 'test', test)

#org_discussions = create_dict_debateorg(path_html + "debateorg/")
#write_dict_to_json(path_data + "debateorg/", 'discussions_debateorg', org_discussions)


