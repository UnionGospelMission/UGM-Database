from django.test import TestCase

from views import report_processor,interactiveConsole,readableList

class BuildFilterTester(TestCase):
    
    def setUp(self):
        self.env = {'print': lambda x: 1,
                    'query':[
                                ['guest1','guest1 data',[['date1','value1'],['date2','value2'],['date3','value3']],[['1date1','1value1'],['1date2','1value2']]],
                                ['guest2','guest2 data',[['2date1','2value1'],['2date2','2value2'],['2date3','2value3']],[['3date1','3value1'],['3date2','3value2']]]
                            ],
                    'query1':[
                                ['guest1','guest1 data',[['date1','value1'],['date2','value2'],['date3','value3']],[['1date1','1value1'],['1date2','1value2']]]
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
                                                                                      
    def test_multifield_variable_query(self):
        # Test queries wanting multiple fields
        self.assertEqual(report_processor.buildFilter(self.env,' $query::0','','',([u'extrafield', u' $query::1', u''],)),[
                                                                                        ['guest1','guest1 data'],
                                                                                        ['guest2','guest2 data']
                                                                                      ])
    
    def test_timeseries_fields_variable_query(self):
        # Test queries requesting whole time series fields
        self.assertEqual(report_processor.buildFilter(self.env,' $query::2','','',()),[
                                        [[['2date1','2value1'],['2date2','2value2'],['2date3','2value3']]],
                                        [[['date1','value1'],['date2','value2'],['date3','value3']]]
                                        
                                    ])
    
    def test_timeseries_fields_variable_second_level_query(self):
        # Test asking for first date value pair of time series field in a variable
        self.assertEqual(report_processor.buildFilter(self.env,' $query::2::0','','',()),[
                                                                                            [['2date1','2value1']],
                                                                                            [['date1','value1']]
                                                                                         ])

    def test_timeseries_fields_variable_second_level_query_with_flag(self):
        # Test asking for first date value pair of time series field in a variable with
        # time series flag
        self.assertEqual(report_processor.buildFilter(self.env,' $query::2::0','','on',()),[
                                                                                            ['2date1','2value1'],
                                                                                            ['date1','value1']
                                                                                         ])
                                                                                         
    def test_multifield_variable_second_level_query(self):
        # Test asking for date and value from time series field
        self.assertEqual(report_processor.buildFilter(self.env,' $query::2::0','','',(['extrafield',' $query::2::1',''],)),[
                                                                                            [['2date1','2value1'],['2date2','2value2']],
                                                                                            [['date1','value1'],['date2','value2']]
                                                                                         ])

    def test_timeseries_fields_variable_third_level_query(self):
        # Test asking for date from first date value pair in time series field in a variable
        self.assertEqual(report_processor.buildFilter(self.env,' $query::2::0::0','','',()),[
                                                                                                ['2date1'],
                                                                                                ['date1']
                                                                                            ])
    
    def test_timeseries_fields_variable_third_level_multi_field_query(self):
        self.assertEqual(report_processor.buildFilter(self.env,' $query::2::0::0','','',(['extrafield',' $query::2::0::1',''],)),[
                                                                                                ['2date1','2value1'],
                                                                                                ['date1','value1']
                                                                                            ])

    def test_timeseries_fields_variable_query_with_flag(self):
        # Test asking for time series field as date value pairs (instead of record of date value pair list)
        self.assertEqual(report_processor.buildFilter(self.env,' $query::2','','on',()),[
                                        [['2date1','2value1'],['2date2','2value2'],['2date3','2value3']],
                                        [['date1','value1'],['date2','value2'],['date3','value3']]
                                    ])
