#!/usr/bin/python3

import json
import re
import os
import argparse
import time

target_manifest = ".repo/manifests/default.xml"
target_gerrit = "gerrit link"
gerrit_user = "user.name"
debugging = True
'''
This script is used to operate gerrit with topic, it has below functions.
1. Cherry-pick multi changes of same topic.
2. Review/submit changes on gerrit for topic
'''

def main():
    parser = argparse.ArgumentParser()
    parser.description = 'Please find below usage.'
    parser.add_argument("-topic", "--topic", help="Gerrit topic name to cherry-pick. \n", default=None, required=False)
    parser.add_argument("-option", "--option", help="Gerrit option: +1/+2/submit", default=None, required=False)
    args = parser.parse_args()
    if (args.topic is not None):
        op_gerrit = gerrit_review(args.topic, args.option)
    else:
        print('Empty option. Please check usage with -h')

# This class is operations for cherry-pick topick from gerrit, or review/submit on gerrit for target topic
class gerrit_review:
    '''
    :param
    topic: targe topic
    gerrit_data: changes index and patchset number on gerrit
    '''
    def __init__(self, topic=None, option=None):
        if (topic is not None):
            self.topic = topic

        self.commits_json = None
        self.gerrit_data = None
        self.load_commits_for_topic()
        if (option is not None):
            # Operate gerrit commits with gerrit query command
            self.option = option
            self.load_commits_info()
            self.execute_review()
        else:
            print("Empty option, will cherry pick commits for topic:" + self.topic)
            self.topic_apply()

    # Load all open commits from gerrit for target topic
    def load_commits_for_topic(self):
        if (self.topic != None):
            topicList = 'topic_change_' + self.topic + '.json'
        else:
            topicList = 'topic_change_temp.json'
        loadTopicCmd = 'ssh -p 29418 ' + target_gerrit + ' gerrit query --format=JSON --current-patch-set topic:' + self.topic + ' status:open > ' + topicList
        os.system(loadTopicCmd)
        self.commits_json = os.path.join(src_root, topicList)
        print('loadTopic - jsonPath:', self.commits_json)
        # [END] load commit for target topic

    # Load gerrit ID and patchset ID for each commit of target topic
    def load_commits_info(self):
        with open(self.commits_json, "r") as data:
            commits = data.readlines()
            data.close()
        commit_info = []
        for one_commit in commits:
            if 'project' in one_commit:
                commitJson = json.loads(one_commit)
                print(commitJson['project'])
                if (commitJson['project'] != None):
                    gerrit_index = commitJson['number']
                    patchset_index = commitJson['currentPatchSet']['number']
                    commit_info.append(str(gerrit_index) + ',' + str(patchset_index))
        self.gerrit_data = commit_info

    def find_project_path(self, branch, pro_name):
        with open(target_manifest, "r") as data_src:
            datas = data_src.read().split('\n')
        data_src.close()
        for x in datas:
            path_re = x.find(pro_name)
            if (path_re != -1):
                revision_dest = re.findall(r"revision=\"(.*?)\"", x)
                if len(revision_dest) > 0:
                    # print("revision_dest: ", revision_dest[0])
                    if (revision_dest[0] == branch):
                        # print(x)
                        dest = re.findall(r"path=\"(.*?)\"", x)
                        if len(dest) > 0:
                            return (dest[0])
                else:
                    dest = re.findall(r"path=\"(.*?)\"", x)
                    if len(dest) > 0:
                        return (dest[0])

    def topic_apply(self):
        with open(self.commits_json, "r") as data:
            commits = data.readlines()
            data.close()
        applys=0
        for commit in commits:
            if 'project' in commit:
                self.execute_apply(commit)
                applys = applys +1
            else: # Get total commits number
                total=json.loads(commit)
                print("Total commit number is:"+total['rowCount'])
        print(applys+" commits were applied!")

    #Cherry pick change
    def execute_apply(self, commit):
        commitJson = json.loads(commit)
        command_pre = 'git fetch "https://' + target_gerrit + '/a/'
        if (commitJson['project'] != None):
            pro_path = self.find_project_path(commitJson['branch'], commitJson['project'])
            print("execute_apply---pro_path:" + pro_path)
            if (pro_path is not None):
                os.chdir(os.path.join(src_root, pro_path))
                if (len(commitJson['currentPatchSet']['parents']) == 1):
                    command = command_pre + commitJson['project'] + '" ' + commitJson['currentPatchSet'][
                        'ref'] + ' && git cherry-pick FETCH_HEAD'
                else:
                    command = command_pre + commitJson['project'] + '" ' + commitJson['currentPatchSet'][
                        'ref'] + ' && git cherry-pick FETCH_HEAD -m 1'
                final_cmd = command + ' > '
                os.system(final_cmd)
                os.chdir(src_root)

    # Execute review for topic
    def execute_review(self):
        if (self.option == 'submit'):
            op_cmd = '--submit'
        elif (self.option == '+1' or self.option == '+2'):
            op_cmd = '--code-review ' + self.option
        for commit in self.gerrit_data:
            command = 'ssh -p 29418 ' + gerrit_user + '@' + target_gerrit + ' gerrit review ' + op_cmd + ' ' + commit
            os.system(command)

if __name__ == '__main__':
    src_root = os.getcwd()
    main()
