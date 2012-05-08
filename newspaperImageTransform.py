import glob
import fnmatch
import os
from os.path import basename
import subprocess
import sys
import xml.dom.minidom
from xml.dom.minidom import Node


# Sub to filter list uniques
def unique_list_filter(seq, idfun=None): 
    # order preserving
    if idfun is None:
        def idfun(x): return x
    seen = {}
    result = []
    for item in seq:
        marker = idfun(item['filename'])
        if marker in seen: continue
        seen[marker] = 1
        result.append(item)
    return result


def mkdir_if_not_exist(dirpath):
    if not os.path.exists(dirpath):
        os.makedirs(dirpath)
        return True
    return False


# Globals
cur_process_tree = []
global_actions = []
files_processed = []

# Parse Input
dom = xml.dom.minidom.parse("./newspaperImageConfig.xml")

# Assign Bins
bins = {
        'convert' : dom.getElementsByTagName('convert')[0].firstChild.nodeValue
        }

global_archive_path = dom.getElementsByTagName('completefilestorepath')[0].firstChild.nodeValue

# Build Globals
process_groups=dom.getElementsByTagName('globalaction')
for cur_action in process_groups:
    global_actions.append(cur_action.firstChild.nodeValue)

# Build Process List.
process_groups=dom.getElementsByTagName('processgroup')
for cur_group in process_groups:
    if cur_group.getElementsByTagName('enabled')[0].firstChild.nodeValue == 'true' :

        for root, dirnames, filenames in os.walk(cur_group.getElementsByTagName('grouppath')[0].firstChild.nodeValue):
            for filename in fnmatch.filter(filenames, '*' + cur_group.getElementsByTagName('groupextension')[0].firstChild.nodeValue):
                active_file_name=os.path.join(root, filename)
                relative_file_path=root.replace(cur_group.getElementsByTagName('grouppath')[0].firstChild.nodeValue + '/','') 

                # Add Current Steps
                for cur_output_item in cur_group.getElementsByTagName('item') :
                    cur_steps=[]

                    for cur_output_step in cur_output_item.getElementsByTagName('step') :
                        cur_steps.append(cur_output_step.firstChild.nodeValue)

                        cur_process_tree.append( {'filename' : active_file_name,
                                                  'steps' : cur_steps,
                                                  'relative_path' : relative_file_path,
                                                  'output_path' : cur_output_item.getElementsByTagName('outputpath')[0].firstChild.nodeValue,
                                                  'outputfilename' : basename(active_file_name).replace( cur_group.getElementsByTagName('groupextension')[0].firstChild.nodeValue,cur_output_item.getElementsByTagName('outputextension')[0].firstChild.nodeValue)
                                                  } )

for cur_step in cur_process_tree :
    bin_string = bins['convert'] + ' ' + cur_step['filename'] + ' ' +' '.join(global_actions) + ' ' + ' '.join(cur_step['steps']) + ' ' + cur_step['output_path'] + '/' + cur_step['relative_path'] + '/' + cur_step['outputfilename']
    mkdir_if_not_exist( cur_step['output_path'] + '/' + cur_step['relative_path'] )
    print bin_string
    # subprocess.call(bin_string, shell=True)

# Move file to processed directory. 
for cur_file_to_move in unique_list_filter(cur_process_tree) :
    full_archive_dir = global_archive_path + '/' + cur_file_to_move['relative_path']
    mkdir_if_not_exist(full_archive_dir)
    print cur_file_to_move['filename'], full_archive_dir + '/' + basename(cur_file_to_move['filename'])
    # subprocess.call(['mv', cur_file_to_move, global_archive_path])
