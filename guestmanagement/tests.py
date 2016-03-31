from django.test import TestCase

from views import report_processor

class BuildFilterTester(TestCase):
    env = {'print': lambda x: 1,
           'query':[
                        ['guest1','guest1 data',[['date1','value1'],['date2','value2'],['date3','value3']],[['1date1','1value1'],['1date2','1value2']]],
                        ['guest2','guest2 data',[['2date1','2value1'],['2date2','2value2'],['2date3','2value3']],[['3date1','3value1'],['3date2','3value2']]]
                   ],
          }

    def test_entire_variable_query(self):
        # Test queries requesting every record from variables
        self.assertEqual(report_processor.buildFilter(self.env,' $query','','',()),[
                                    ['guest1','guest1 data',[['date1','value1'],['date2','value2'],['date3','value3']],[['1date1','1value1'],['1date2','1value2']]],
                                    ['guest2','guest2 data',[['2date1','2value1'],['2date2','2value2'],['2date3','2value3']],[['3date1','3value1'],['3date2','3value2']]]
                                 ])

    def test_fields_variable_query(self):
        # Test queries requesting normal fields from variables
        self.assertEqual(report_processor.buildFilter(self.env,' $query::0','','',()),[
                                                                                        ['guest1'],
                                                                                        ['guest2']
                                                                                      ])
    
    def test_timeseries_fields_variable_query(self):
        # Test queries requesting whole time series fields
        self.assertEqual(report_processor.buildFilter(self.env,' $query::2','','',()),[
                                        [[['2date1','2value1'],['2date2','2value2'],['2date3','2value3']]],
                                        [[['date1','value1'],['date2','value2'],['date3','value3']]]
                                        
                                    ])
