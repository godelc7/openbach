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


"""Provide time period summary of data generated by OpenBACH jobs"""


__author__ = 'Viveris Technologies'
__credits__ = '''Contributors:
 * Aichatou Garba Abdou <aichatou.garba-abdou@viveris.fr>
'''

import os
import itertools
import tempfile
import argparse
import syslog

from dateutil.parser import parse
from datetime import datetime,timedelta
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

import collect_agent
from data_access.post_processing import Statistics, save, _Plot


COLUMN_NUMBER=4
FUNCTION_DIC={'mean':'Moyenne','median':'Médiane','min':'Minimum','max':'Maximum'}
UNIT_OPTION={'s', 'ms' ,'bits/s', 'Kbits/s', 'Mbits/s','Gbits/s','Bytes' ,'KBytes', 'MBytes', 'GBytes'}


def multiplier(base, unit):
        if unit == base:
                return 1
        if unit.startswith('GBytes'):
                return 1024 * 1024 * 1024
        if unit.startswith('MBytes'):
                return 1024 * 1024
        if unit.startswith('KBytes'):
                return 1024
        if unit.startswith('m'):
                return 0.001
        if unit.startswith('s'):
                return 1000
        if unit.startswith('Gbits'):
                return 1000 * 1000 * 1000
        if unit.startswith('Mbits'):
                return 1000 * 1000
        if unit.startswith('Kbits'):
                return 1000
        return 1


def plot_summary_agent_comparison(
                                axis,function_result,reference,agent,
                                num_bar,filled_box):
                                  
        if axis is None:
            _,axis=plt.subplot()

        axis[0].axis([0, 10, 0, 10])  
        axis[0].text(.1,.5,agent,fontsize=10,transform=axis[0].transAxes)
        axis=axis[1:]
        step=int(100/num_bar)
        for (axe,value) in zip(axis,function_result):

            if reference is not None:
                
                if value >=0 and value <= (reference*1/num_bar):
                    height=[step]                   
                if value >(reference*1/num_bar) and value <= (reference*2/num_bar):
                    height=range(step,3*step,step)
                if value >(reference*2/num_bar) and value <= (reference*3/num_bar):
                    height=range(step,4*step,step)
                if value >(reference*3/num_bar) and value <= (reference*4/num_bar):
                    height=range(step,5*step,step)
                if value >(reference*4/num_bar) :
                    height=range(step,6*step,step)

                if not filled_box:
                    bars_template=range(step,(num_bar+1)*step,step)
                    nb_bars_template=np.arange(len(bars_template))
                    axe.bar(nb_bars_template,bars_template,width=0.7,color=(0.1, 0.1, 0.1, 0.2)) 
                    
                    nb_bars=np.arange(len(height))
                    axe.bar(nb_bars,height,width=0.7,color='black')
                    axe.text(-0.3,80,str(round(value,2)),fontsize=7)
                else:
                    axe.set(ylim=(0,10))
                    bar_position=[3]
                    axe.barh(bar_position,[100],height=3,align='center',color=(0.1, 0.1, 0.1, 0.2))
                    percent=round((value*100)/reference,1)
                    axe.barh(bar_position,[percent],height=3,align='center',color='black')
                    axe.text(1,8,f'{str(round(value,2))} ({str(percent)}%)',fontsize=8)
            else:

               axe.axis([0, 10, 0, 10])   
               axe.text(3,5,str(round(value,2)),fontsize=10)

        return axis  
def main(
        agents_name,job_name,statistic_name,begin_date,end_date,function,reference,num_bars,start_journey,start_evening,start_night,
        stat_unit,table_unit,agents_title,stat_title,figure_title,stats_with_suffixes,filled_box):
     
    file_ext = 'png'
    statistics = Statistics.from_default_collector()
    statistics.origin = 0
    with tempfile.TemporaryDirectory(prefix='openbach-summary_agent_comparison-') as root:
        if not begin_date and not end_date:
                timestamp=None
        else:
                begin_date=parse(begin_date)
                end_date=parse(end_date)
                timestamp=[int(datetime.timestamp(begin_date)*1000),int(datetime.timestamp(end_date)*1000)]

        if not function :
                function='moyenne' 

        if not start_journey :
                start_journey=7
        if not start_evening :
                start_evening=18
        if not start_night :
                start_night=0 
        if not num_bars:
                num_bar=5

        if not stat_title :
                stat_title=statistic_name

        if not table_unit:
                table_unit=''
        
        facteur=multiplier(stat_unit,table_unit)
        
        

        rows_number=len(agents_name)
        
        figure, axis = plt.subplots(rows_number+1,COLUMN_NUMBER)
        plt.subplots_adjust(hspace=0,wspace=0)
        _axis_list=list(axis)

        moments=[f' {FUNCTION_DIC[function]} \n {stat_title} \n {table_unit}',f'Journée ({start_journey}h-{start_evening}h)',
                        f'Soirée ({start_evening}h-{start_night}h)',f'Nuit ({start_night}h-{start_journey}h)']
        
        for moment,axe in zip(moments,_axis_list[0]): 
                axe.axis([0, 10, 0, 10])   
                axe.text(.5,3,moment,fontsize=10)

        for axe in axis.flat:
                axe.tick_params(
                                which='both',      
                                bottom=False,
                                left=False,      
                                top=False,  
                                labelleft = False,       
                                labelbottom=False)

        if not agents_title:
                agents_title=agents_name

        for (index, agent),agent_title in itertools.zip_longest(enumerate(agents_name),agents_title,fillvalue=None):
                
                if agent_title is None:
                        agent_title=agent


                data_collection = statistics.fetch_all(
                        job=job_name,agent=agent,
                        suffix = None if stats_with_suffixes else '',
                        fields=[statistic_name],timestamps=timestamp)
                

                function_result=data_collection.compute_function(
                                                function,facteur,
                                                start_journey,start_evening,start_night)

                axis=plot_summary_agent_comparison(_axis_list[index+1],function_result,reference,
                                                        agent_title,num_bar,filled_box,)

        if figure_title :
                axis.set_title(figure_title)       
        filepath = os.path.join(root, 'summary_agent_comparison_{}.{}'.format(statistic_name, file_ext))     
        save(figure,filepath,set_legend=False)
        collect_agent.store_files(collect_agent.now(), figure=filepath)
                



if __name__ == '__main__':
   with collect_agent.use_configuration('/opt/openbach/agent/jobs/summary_agent_comparison/summary_agent_comparison_rstats_filter.conf'):
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument(
                metavar='AGENT_NAME',dest='agents',nargs='+',
                type=str, default=[],help='Agent name to fetch data from')
        parser.add_argument(
                metavar='JOB_NAME',type=str, default=[],dest='jobs',
                help='job name to fetch data from')
        parser.add_argument(
                metavar='STATISTIC',dest='statistics',default=[],
                help='statistics names to be analysed')
        parser.add_argument(
                '-b', '--begin-date',metavar='BIGIN_DATE',dest='begin_date',
                default=[],help='Start date in format YYYY:MM:DD hh:mm:ss')
        parser.add_argument(
                '-e', '--end-date',metavar='END_DATE',dest='end_date',
                default=[],help='End date in format YYYY:MM:DD hh:mm:ss')
        parser.add_argument(
                '-f', '--function', dest='function',choices=list(FUNCTION_DIC),
                metavar='FUNCTION',default=[],help='Mathematical function to compute')
        parser.add_argument(
                '-r', '--reference',metavar='REFERENCE',dest='reference',type=int,
                default=[],help='Reference value for comparison')
        parser.add_argument(
                '-nb', '--num-bars',metavar='NUM_BARS',dest='num_bars',type=int,default=[],
                help='Number of reception bars')
        parser.add_argument(
                '-sj', '--start-journey',metavar='START_JOURNEY',dest='start_journey',type=int,
                default=[],help='starting time of the day')
        parser.add_argument(
                '-se', '--start-evening',metavar='START_EVENING',dest='start_evening',type=int,
                default=[],help='starting time of the evening')
        parser.add_argument(
                '-sn', '--start-night',metavar='START_NIGHT',dest='start_night',type=int,
                default=[],help='starting time of the night')
        parser.add_argument(
                '-ub', '--stat-unit', dest='stat_units', choices=UNIT_OPTION,
                metavar='STAT_UNIT', default=[],help='Unit of the statistic')
        parser.add_argument(
                '-u', '--table-unit', dest='table_units', choices=UNIT_OPTION,
                metavar='TALE_UNIT', default=[],help='Desired unit to show on the figure')
        parser.add_argument(
                '-a', '--agent-title', metavar='AGENT_TITLE ', nargs='+',dest='agents_title',
                type=str, default=[],help='Agent name to display on the table')
        parser.add_argument(
                '-s', '--stat-title', dest='stat_title',metavar='STAT-TITLE',default=[],
                help='statistics names to display on the figure')
        parser.add_argument(
                '-t','--title', dest='figure_title',metavar='FIGURE_TITLE',default=[],
                help=' The title of the generated figure')
        parser.add_argument(
                '-w', '--no-suffix', action='store_true',
                help='Do not plot statistics with suffixes')
        parser.add_argument(
                '-g', '--filled-box', action='store_true',
                help='Display stats value in a filled box')

        args = parser.parse_args()
        stats_with_suffixes = not args.no_suffix
        

        main(
            args.agents,args.jobs, args.statistics,args.begin_date,args.end_date,args.function,args.reference,args.num_bars,args.start_journey,args.start_evening,
            args.start_night,args.stat_units,args.table_units,args.agents_title,args.stat_title,args.figure_title ,stats_with_suffixes,args.filled_box)
