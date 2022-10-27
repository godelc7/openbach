#!/usr/bin/env python3

# OpenBACH is a generic testbed able to control/configure multiple
# network/physical entities (under test) and collect data from them. It is
# composed of an Auditorium (HMIs), a Controller, a Collector and multiple
# Agents (one for each network entity that wants to be tested).
#
#
# Copyright © 2016-2020 CNES
#
#
# This file is part of the OpenBACH testbed.
#
#
# OpenBACH is a free software : you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY, without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see http://www.gnu.org/licenses/.


"""Provide time series of data generated by OpenBACH jobs"""


__author__ = 'Viveris Technologies'
__credits__ = '''Contributors:
 * David FERNANDES <david.fernandes@viveris.fr>
'''

from copy import copy
import sys
import syslog
import os.path
import argparse
import tempfile
import itertools

import pandas as pd
import matplotlib.pyplot as plt

#import collect_agent
from data_access.post_processing import Statistics, save, _Plot


TIME_OPTIONS = {'year', 'month', 'day', 'hour', 'minute', 'second'}


def main(
        job_instance_ids, statistics_names, aggregations_periods, percentiles,
        stats_with_suffixes, axis_labels, figures_titles, use_legend,hide_grid, median,
        average, deviation, boundaries, min_max, pickle):

    file_ext = 'pickle' if pickle else 'png'
    #statistics = Statistics.from_default_collector()
    statistics=Statistics('172.20.34.80')
    statistics.origin = 0
    with tempfile.TemporaryDirectory(prefix='openbach-temporal-binning-statistics-') as root:
        for job, fields, aggregations, labels, titles in itertools.zip_longest(
                job_instance_ids, statistics_names, aggregations_periods, axis_labels, figures_titles,
                fillvalue=[]):
            data_collection = statistics.fetch(
                    job_instances=job,
                    suffix = None if stats_with_suffixes else '',
                    fields=fields)
            
            # Drop multi-index columns to easily concatenate dataframes from their statistic names
            df = pd.concat([
                plot.dataframe.set_axis(plot.dataframe.columns.get_level_values('statistic'), axis=1, copy=False)
                for plot in data_collection])
            
            # Recreate a multi-indexed columns so the plot can function properly
            df.columns = pd.MultiIndex.from_tuples(
                    [('', '', '', '', stat) for stat in df.columns],
                    names=['job', 'scenario', 'agent', 'suffix', 'statistic'])  
            
            plot = _Plot(df)

            if not fields:
                fields = list(df.columns.get_level_values('statistic'))

            for field, label, aggregation, title in itertools.zip_longest(fields, labels, aggregations, titles):
                if field not in df.columns.get_level_values('statistic'):
                    message = 'job instances {} did not produce the statistic {}'.format(job, field)
                    #collect_agent.send_log(syslog.LOG_WARNING, message)
                    print(message)
                    continue

                if label is None:
                    """collect_agent.send_log(
                            syslog.LOG_WARNING,
                            'no y-axis label provided for the {} statistic of job '
                            'instances {}: using the empty string instead'.format(field, job))"""
                    label = ''

                if aggregation is None:
                    """collect_agent.send_log(
                            syslog.LOG_WARNING,
                            'invalid aggregation value of {} for the {} '
                            'statistic of job instances {}: choose from {}, using '
                            '"hour" instead'.format(aggregation, field, job, TIME_OPTIONS))"""
                    aggregation = 'hour'

                figure, axis = plt.subplots()
                
                axis = plot.plot_temporal_binning_statistics(
                        axis, label, field, None,
                        percentiles, aggregation,
                        median, average, deviation, boundaries,
                        min_max, use_legend,hide_grid)
                if title is not None:
                    axis.set_title(title)
                filepath = os.path.join(root, 'temporal_binning_statistics_{}.{}'.format(field, file_ext))
                #save(figure, filepath, pickle)
                save(figure, '/home/agarba-abdou/openbach-extra/apis/temporal_binding_statistics.png',False)
                #collect_agent.store_files(collect_agent.now(), figure=filepath)


if __name__ == '__main__':
    #with collect_agent.use_configuration('/opt/openbach/agent/jobs/temporal_binning_statistics/temporal_binning_statistics_rstats_filter.conf'):
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument(
                '-j', '--jobs', metavar='ID', nargs='+', action='append',
                required=True, type=int, default=[],
                help='job instances to plot data from')
        parser.add_argument(
                '-s', '--stat', '--statistic', dest='statistics',
                metavar='STATISTIC', nargs='+', action='append', default=[],
                help='statistics names to plot')
        parser.add_argument(
                '-a', '--aggregation', dest='aggregations', type=str,
                choices=TIME_OPTIONS, nargs='+', action='append',
                help='Time criteria for values aggregation')
        parser.add_argument(
                '--percentiles', '--percentiles-covering',
                metavar=('PERCENTILE', 'PERCENTILE'), nargs=2, action='append', type=int,
                help='Percentiles in percentages. Color will be filled between them.'
                        '(Maximum allowed is 2 pairs of percentiles)')
        parser.add_argument(
                '-w', '--no-suffix', action='store_true',
                help='do not plot statistics with suffixes')
        parser.add_argument(
                '-y', '--ylabel', dest='ylabel', nargs='+',
                metavar='YLABEL', action='append', default=[],
                help='the label of y-axis')
        parser.add_argument(
                '-t', '--title', dest='title', nargs='+',
                metavar='TITLE', action='append', default=[],
                help='the title of figure')
        parser.add_argument(
                '-p', '--pickle', action='store_true',
                help='allows to export figures as pickle '
                '(by default figures are exported as image)')
        parser.add_argument(
                '-n', '--hide-legend', '--no-legend', action='store_true',
                help='do not draw any legend on the graph')
        parser.add_argument(
                '-d', '--hide-grid', '--no-grid', action='store_true',
                help='do not show grid on the graph')
        parser.add_argument(
                '--hide-median', '--no-median', action='store_true',
                help='do not draw median on the graph')
        parser.add_argument(
                '--hide-average', '--no-average', action='store_true',
                help='do not draw average on the graph')
        parser.add_argument(
                '--hide-percentiles', '--no-percentiles', action='store_true',
                help='do not draw nor fill color between percentiles on the graph')
        parser.add_argument(
                '--hide-deviation', '--no-deviation', action='store_true',
                help='do not draw deviation on the graph')
        parser.add_argument(
                '--hide-boundaries', '--no-boundaries', action='store_true',
                help='do not draw boundaries on the graph')
        parser.add_argument(
                '--hide-min-max', '--no-min-max', action='store_true',
                help='do not fill color between boundaries on the graph')

        args = parser.parse_args()
        stats_with_suffixes = not args.no_suffix
        use_legend = not args.hide_legend
        draw_median = not args.hide_median
        draw_average = not args.hide_average
        draw_percentiles = not args.hide_percentiles
        draw_deviation = not args.hide_deviation
        draw_boundaries = not args.hide_boundaries
        draw_min_max = not args.hide_min_max
        hide_grid = not args.hide_grid

        if not draw_percentiles :
            args.percentiles = None
        elif args.percentiles is None:
            args.percentiles = [[5, 95], [25, 75]]
        elif len(args.percentiles) > 2 :
            message = 'Too many percentile pairs. Maximum allowed is 2 pairs.'
            #collect_agent.send_log(syslog.LOG_ERR, message)
            sys.exit(message)

        main(args.jobs, args.statistics, args.aggregations, args.percentiles, stats_with_suffixes,
                args.ylabel, args.title, use_legend,hide_grid, draw_median, draw_average,
                draw_deviation, draw_boundaries, draw_min_max, args.pickle)
