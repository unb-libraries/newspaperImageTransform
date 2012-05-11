import glob
import fnmatch
import os
from os.path import basename
import re
import subprocess
import sys
import tempfile
from time import localtime, strftime
import xml.dom.minidom
from xml.dom.minidom import Node


def log_write(msg): 
    print strftime("%a, %d %b %Y %H:%M:%S", localtime()) + ' | ' + msg
    return True


# Sub to filter list uniques
def unique_list_filter(seq, idfun=None) :
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


def delete_if_exists(filename) :
    if os.path.isfile(filename) :
        os.unlink(filename)
    return True 


# Determine parity of page number
def get_page_parity(filename):
    if re.search(".*_.*_.*_[0-9]{3}\.",filename) != None :
        if re.search(".*_.*_.*_[0-9]{2}[13579]\.",filename) == None :
            return 'even'
        return 'odd'
    return 'unknown'


def generate_tmp_filename(filename,global_temp_directory,cur_file_extension) :
    return global_temp_directory + '/' + basename(filename).replace(cur_file_extension,'.png')


def convert_tmp_tiff(convert_bin,tmp_filename,steps,string_to_use) :
    if len(steps) > 0 :
        convert_cmd_string = convert_bin + ' ' + tmp_filename + ' -compress None -strip ' + ' '.join(steps) + ' ' + tmp_filename
        log_write("Applying Global / Group Transform [" + string_to_use + "] : " + convert_cmd_string)
        subprocess.call(convert_cmd_string, shell=True)
        return True
    return False


# Globals
cur_process_tree = []
global_action_queue = []

# Parse Input
dom = xml.dom.minidom.parse("./newspaperImageConfig.xml")

# Assign Bins
bins = {
        'convert' : dom.getElementsByTagName('convert')[0].firstChild.nodeValue,
        }

global_archive_path = dom.getElementsByTagName('completefilestorepath')[0].firstChild.nodeValue
global_temp_directory = tempfile.mkdtemp()

# Build Globals
process_groups=dom.getElementsByTagName('globalaction')
for cur_action in process_groups:
    global_action_queue.append(cur_action.firstChild.nodeValue)

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
                    item_actions=[]
                    global_actions=[]
                    global_parity_actions=[]
                    group_actions=[]
                    group_parity_actions=[]

                    global_actions.extend(global_action_queue)

                    for cur_group_step in cur_group.getElementsByTagName('groupaction') :
                        group_actions.append(cur_group_step.firstChild.nodeValue)

                    cur_parity_val=get_page_parity(filename)

                    if cur_parity_val == 'even' :
                        for cur_parity_step in dom.getElementsByTagName('globalevenaction') :
                            global_parity_actions.append(cur_parity_step.firstChild.nodeValue)
                        for cur_parity_step in dom.getElementsByTagName('groupevenaction') :
                            group_parity_actions.append(cur_parity_step.firstChild.nodeValue)
                        for cur_parity_step in cur_output_item.getElementsByTagName('itemevenaction') :
                            item_actions.append(cur_parity_step.firstChild.nodeValue)

                    if cur_parity_val == 'odd' :
                        for cur_parity_step in dom.getElementsByTagName('globaloddaction') :
                            global_parity_actions.append(cur_parity_step.firstChild.nodeValue)
                        for cur_parity_step in dom.getElementsByTagName('groupoddaction') :
                            group_parity_actions.append(cur_parity_step.firstChild.nodeValue)
                        for cur_parity_step in cur_output_item.getElementsByTagName('itemoddaction') :
                            item_actions.append(cur_parity_step.firstChild.nodeValue)

                    for cur_output_step in cur_output_item.getElementsByTagName('itemaction') :
                        item_actions.append(cur_output_step.firstChild.nodeValue)

                    cur_process_tree.append( {'name' : cur_output_item.getElementsByTagName('itemdescription')[0].firstChild.nodeValue,
                                              'filename' : active_file_name,
                                              'item-actions' : item_actions,
                                              'group-actions' : group_actions,
                                              'group-parity-actions' : group_parity_actions,
                                              'global-actions' : global_actions,
                                              'global-parity-actions' : global_parity_actions,
                                              'relative_path' : relative_file_path,
                                              'output_path' : cur_output_item.getElementsByTagName('outputpath')[0].firstChild.nodeValue,
                                              'outputfilename' : basename(active_file_name).replace( cur_group.getElementsByTagName('groupextension')[0].firstChild.nodeValue,cur_output_item.getElementsByTagName('outputextension')[0].firstChild.nodeValue)
                                              } )

last_tmps_generated_for=''

for cur_step in cur_process_tree :
    cur_file_name, cur_file_extension = os.path.splitext(cur_step['filename'])

    # Generate temporary filename string
    tmp_filename = generate_tmp_filename(cur_step['filename'],global_temp_directory,cur_file_extension)

    if last_tmps_generated_for != cur_step['filename'] :

        if last_tmps_generated_for != '' :
            log_write("Finished Processing : " + last_tmps_generated_for + "\n")
        log_write("Starting Processing : " + cur_step['filename'])
        # Delete last tmp file.
        delete_if_exists(generate_tmp_filename(last_tmps_generated_for,global_temp_directory,cur_file_extension))

        # Step 1 (Convert To PNG)
        stage1_bin_string = bins['convert'] + ' ' + cur_step['filename'] + ' -compress None -strip ' + tmp_filename
        log_write("Generating Global Intermediate : " + stage1_bin_string)
        subprocess.call(stage1_bin_string, shell=True)

        # Step 2 (Convert Global/Group Actions)
        convert_tmp_tiff(bins['convert'],tmp_filename,cur_step['global-actions'],'global-actions')
        convert_tmp_tiff(bins['convert'],tmp_filename,cur_step['global-parity-actions'],'global-parity-actions')
        convert_tmp_tiff(bins['convert'],tmp_filename,cur_step['group-actions'],'group-actions')
        convert_tmp_tiff(bins['convert'],tmp_filename,cur_step['group-parity-actions'],'group-parity-actions')
        convert_tmp_tiff(bins['convert'],tmp_filename,cur_step['group-post-actions'],'group-post-actions')

        last_tmps_generated_for=cur_step['filename']

    # Generate final output for item.
    bin_string = bins['convert'] + ' ' + tmp_filename + ' ' + ' '.join(cur_step['item-actions']) + ' ' + cur_step['output_path'] + '/' + cur_step['relative_path'] + '/' + cur_step['outputfilename']
    mkdir_if_not_exist( cur_step['output_path'] + '/' + cur_step['relative_path'] )
    log_write("Generating " + cur_step['name'] + " Output : " + bin_string)
    subprocess.call(bin_string, shell=True)


# Move file to processed directory. 
for cur_file_to_move in unique_list_filter(cur_process_tree) :
    full_archive_dir = global_archive_path + '/' + cur_file_to_move['relative_path']
    mkdir_if_not_exist(full_archive_dir)
    log_write("Finished, Moving Original File To Archive : " + cur_file_to_move['relative_path'])
    # print cur_file_to_move['filename'], full_archive_dir + '/' + basename(cur_file_to_move['filename'])
    # subprocess.call(['mv', cur_file_to_move, global_archive_path])

