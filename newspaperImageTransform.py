import glob
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
        marker = idfun(item)
        if marker in seen: continue
        seen[marker] = 1
        result.append(item)
    return result


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
        for active_file_name in glob.iglob( cur_group.getElementsByTagName('grouppath')[0].firstChild.nodeValue +
                                            cur_group.getElementsByTagName('groupextension')[0].firstChild.nodeValue ) :

            # Add Current Steps
            for cur_output_item in cur_group.getElementsByTagName('item') :
                cur_steps=[]

                for cur_output_step in cur_output_item.getElementsByTagName('step') :
                    cur_steps.append(cur_output_step.firstChild.nodeValue)

                # Add Output Location
                cur_steps.append(
                                 cur_output_item.getElementsByTagName('outputpath')[0].firstChild.nodeValue +
                                 '/' +
                                 basename(active_file_name).replace( cur_group.getElementsByTagName('groupextension')[0].firstChild.nodeValue,
                                                                     cur_output_item.getElementsByTagName('outputextension')[0].firstChild.nodeValue)
                                 )
                cur_process_tree.append( { active_file_name : cur_steps } )

for cur_step in cur_process_tree :
    bin_string = bins['convert'] + ' ' + cur_step.keys()[0] + ' ' + ' '.join(global_actions) + ' ' + ' '.join(cur_step.values()[0])
    print bin_string
    subprocess.call(bin_string, shell=True)
    files_processed.append(cur_step.keys()[0])

# Get Unique file list to move. 
for cur_file_to_move in unique_list_filter(files_processed) :
    subprocess.call(['mv', cur_file_to_move, global_archive_path])
