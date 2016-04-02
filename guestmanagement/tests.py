from django.test import TestCase

from views import report_processor,interactiveConsole,readableList
from cStringIO import StringIO

class BuildFilterTester(TestCase):
    
    def setUp(self):
        self.env = {'print': lambda x: 1,
                    'query':[
                                ['guest1','guest1 data',[['date1','value1'],['date2','value2'],['date3','value3']],[['1date1','1value1'],['1date2','1value2']]],
                                ['guest2','guest2 data',[['2date1','2value1'],['2date2','2value2'],['2date3','2value3']],[['3date1','3value1'],['3date2','3value2']]]
                            ],
                    'query1':['last_name','first_name','checkin_staff','01/31/1956'],
                    'query2':['last_name','first_name','checkin_staff',[['01/31/1956','2'],['01/31/1956','3']]],
                    'id1':'0','id2':'1',
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
                        
    def test_filtering_from_single_records(self):
        # Test asking for values from a single record
        self.assertEqual(report_processor.buildFilter(self.env,' $query1::0','','',([u'extrafield', u' $query1::1', u''],)),[[
                                        'last_name',
                                        'first_name'
                                        ]])

    def test_criteria_filters(self):
        # Test asking for all fields with criteria
        
        # Regular filter with and and or criteria
        self.assertEqual(report_processor.buildFilter(self.env,' $query','','',(['and','=','guest1',' $query::0',''],['or','=','guest2',' $query::0',''])),[
                                    ['guest1','guest1 data',[['date1','value1'],['date2','value2'],['date3','value3']],[['1date1','1value1'],['1date2','1value2']]],
                                    ['guest2','guest2 data',[['2date1','2value1'],['2date2','2value2'],['2date3','2value3']],[['3date1','3value1'],['3date2','3value2']]]
                                 ])
        
        # Regular filter with just and criteria
        self.assertEqual(report_processor.buildFilter(self.env,' $query','','',(['and','=','guest1',' $query::0',''],)),[
                                    ['guest1','guest1 data',[['date1','value1'],['date2','value2'],['date3','value3']],[['1date1','1value1'],['1date2','1value2']]],
                                 ])
                                 
        # Regular filter with reversed and and or criteria
        self.assertEqual(report_processor.buildFilter(self.env,' $query','','',(['or','=','guest2',' $query::0',''],['and','=','guest1',' $query::0',''])),[])
        
        # Regular filter with two or criteria
        self.assertEqual(report_processor.buildFilter(self.env,' $query','','',(['or','=','guest2',' $query::0',''],['or','contains','guest1',' $query::1',''])),[
                                    ['guest1','guest1 data',[['date1','value1'],['date2','value2'],['date3','value3']],[['1date1','1value1'],['1date2','1value2']]],
                                    ['guest2','guest2 data',[['2date1','2value1'],['2date2','2value2'],['2date3','2value3']],[['3date1','3value1'],['3date2','3value2']]]
                                ])

        # Regular filter with two or and one and criteria
        self.assertEqual(report_processor.buildFilter(self.env,' $query','','',(['or','=','guest2',' $query::0',''],['or','contains','guest1',' $query::1',''],['and','=','date1',' $query::2::0::0',''])),[
                                    ['guest1','guest1 data',[['date1','value1'],['date2','value2'],['date3','value3']],[['1date1','1value1'],['1date2','1value2']]],
                                ])
                                
        # Regular second level filter with and criteria
        self.assertEqual(report_processor.buildFilter(self.env,' $query::2','','',(['and','contains','date2',' $query::2','on'],)),[
                                    [[['date1','value1'],['date2','value2'],['date3','value3']]]
                                ])
        
        # Time series second level filter with second level time series and criteria
        self.assertEqual(report_processor.buildFilter(self.env,' $query::2','','on',(['and','contains','date2',' $query::2','on'],)),[
                                    [['date2','value2']]
                                ])
        
        # Time series second level filter with second level time series and criteria and third level time series or criteria
        self.assertEqual(report_processor.buildFilter(self.env,' $query::2','','on',(['and','contains','date2',' $query::2','on'],['or','=','value1',' $query::2::1','on'])),[
                                    [['date1','value1'],['date2','value2']]
                                ])
        

    def test_variable_element_queries(self):
        # Test filters where element ids are contained in variables
        self.assertEqual(report_processor.buildFilter(self.env,' $query::$id1','','',([u'extrafield', u' $query::$id2', u''],)),[
                                                                                        ['guest1','guest1 data'],
                                                                                        ['guest2','guest2 data']
                                                                                      ])
    
    def test_entire_variable_return(self):
        # Test that filters wanting the entire variable return a mutable copy of the original variable
        query = report_processor.buildFilter(self.env,' $query1','','',())
        query[0][0] = []
        self.assertEqual(self.env['query1'],[[],'first_name','checkin_staff','01/31/1956'])
        
    def test_filters_against_varying_length_lists(self):
        # Test for filters against lists which vary in length should return '' for missing elements
        self.assertEqual(report_processor.buildFilter(self.env,' $query::2::3','','',([u'extrafield', u' $query::2::0', u''],)),[
                                                                                        ['',['date1','value1']],
                                                                                        ['',['2date1','2value1']]
                                                                                      ])
    
    def test_timeseries_fields_variable_against_one_record(self):
        # Test single record requesting timeseries field
        
        # Without criteria
        '''
        self.assertEqual(report_processor.buildFilter(self.env,' $query2::3','','on',()),[
                                                    ['01/31/1956', '2'], ['01/31/1956', '3']
                                                                ])
        '''
        # With criteria
        self.assertEqual(report_processor.buildFilter(self.env,' $query2::3','','on',(['and','=','2','$query2::3::1','on'],)),[
                                                    ['01/31/1956', '2']
                                                                ])
        

class DisplayTester(TestCase):


    def setUp(self):
        self.env = {
                    'query':[
                                ['guest1','guest1 data',[['date1','value1'],['date2','value2'],['date3','value3']],[['1date1','1value1'],['1date2','1value2']]],
                                ['guest2','guest2 data',[['2date1','2value1'],['2date2','2value2'],['2date3','2value3']],[['3date1','3value1'],['3date2','3value2']]]
                            ],
                    'query1':['last name','first name','checkin staff','01/31/1956'],
                    }
          

    def test_display(self):
        output = StringIO()
        self.env.update({'print':output.write})
        report_processor.display(self.env,'$query::0','','',['extrafield','$query::1',''])
        report_processor.display(self.env,'$query::0','','',['extrafield','$query::1',''],['and','=','guest1',' $query::0',''])
        self.assertEqual(output.getvalue(),'filter returned more than one valueguest1guest1 data')
        output.close()

        output = StringIO()
        self.env.update({'print':output.write})
        report_processor.display(self.env,'$query1::0',', ','',['extrafield','$query1::0',''])
        report_processor.buildFilter(self.env,' $query1::0','','',([u'extrafield', u' $query1::1', u''],))
        self.assertEqual(output.getvalue(),'last name, last name')
        output.close()
