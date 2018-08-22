#! coding: utf-8
from datetime import datetime, date, timedelta
import json
import os
from dateutil.relativedelta import relativedelta
from gitlab import Gitlab


work_dir = os.path.dirname(os.path.abspath(__file__))
config = {}
with open('%s/config.json' % work_dir) as f:
    config = json.load(f)

gl = Gitlab(
        config['gitlab_host'],
        private_token=config['access_token']
        )


def parse_date(date_str):
    return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S.%f%z').date()


class Rule(object):
    @classmethod
    def rule_name(cls):
        return 'Rule'

    @classmethod
    def is_target(cls, branch):
        return True

    @classmethod
    def match(cls, branch):
        return True


class CommittedDateFilterMixin(object):
    @classmethod
    def get_threshold_date(cls):
        return date.today() - relativedelta(months=1)

    @classmethod
    def match(cls, branch):
        committed_date = parse_date(
                branch.commit.get('committed_date')
                )
        if (
                committed_date
                < cls.get_threshold_date()
                ):
            return True


class MergedCheckRule(Rule):
    @classmethod
    def rule_name(cls):
        return 'merged_check'

    @classmethod
    def is_target(cls, branch):
        return branch.name != 'master'

    @classmethod
    def match(cls, branch):
        return branch.merged


class DevCheckRule(CommittedDateFilterMixin, Rule):
    @classmethod
    def rule_name(cls):
        return 'dev_branch_check'

    @classmethod
    def is_target(cls, branch):
        return branch.name.startswith('dev/')


class TempBranchCheckRule(CommittedDateFilterMixin, Rule):
    @classmethod
    def rule_name(cls):
        return 'temp_branch_check'

    @classmethod
    def is_target(cls, branch):
        return not (
                branch.name == 'master'
                or branch.name.startswith('dev/')
                )

    @classmethod
    def get_threshold_date(cls):
        return date.today() - timedelta(days=7)


RULES = (MergedCheckRule, TempBranchCheckRule, DevCheckRule, )


class BranchInfo(object):
    def __init__(
            self, proj_name, branch_name,
            committer_name, committed_date, merged
            ):
        self.__proj_name = proj_name
        self.__branch_name = branch_name
        self.__committer_name = committer_name
        self.__committed_date = committed_date
        self.__merged = merged

    def __str__(self):
        return (
                'proj_name=%s, branch_name=%s, ' % (
                    self.__proj_name, self.__branch_name,
                    )
                + 'committer_name=%s, committed_date=%s, merged=%s' % (
                    self.__committer_name, str(self.__committed_date),
                    str(self.__merged),
                    )
                )


def main():
    import sys
    group_name = sys.argv[1]
    results = {}
    for group_name in (group_name, ):
        for grp_proj in gl.groups.get(group_name).projects.list(as_list=False):
            proj = gl.projects.get(grp_proj.id)
            for branch in proj.branches.list(as_list=False):
                for rule in RULES:
                    if rule.is_target(branch) and rule.match(branch):
                        info = BranchInfo(
                                proj.name, branch.name,
                                branch.commit.get('committer_name'),
                                branch.commit.get('committed_date'),
                                branch.merged
                                )
                        info_list = results.get(rule.rule_name(), [])
                        info_list.append(info)
                        results[rule.rule_name()] =  info_list
                        break
    for rule_name, info_list in results.items():
        print(rule_name)
        for info in info_list:
            print('    %s' % str(info))


def get_branch(project_id):
    proj = gl.projects.get(project_id)
    return proj.branches.list()

if __name__ == '__main__':
    main()
