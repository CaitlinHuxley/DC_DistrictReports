import pandas as pd

# Reads your statewide voterfile into a dataframe
VoteFile = pd.read_csv('Statefile.csv')

# List of the districts to create into reports
# If you want to run a report of anything else, add it into this list following this format:
# ['ColumnName','ReportName']
DistList = [['CDName', 'Congress'],
            ['LDName', 'State House'],
            ['SDName', 'State Senate'],
            ['CountyName', 'County']]

# CAUTION DON'T CHANGE ANYTHING BELOW THIS UNLESS YOU KNOW WHAT YOU'RE DOING

# later we're going to run a pivot table, and will want to count registered voters
VoteFile['Registration'] = 1

# before we start tagging voters, we set all these to 0
SetZeroList = ['LikelyTurnout_Rep',
               'LikelyTurnout_Dem',
               'LikelyTurnout_Swing',
               'GOTV_Targets']
for z in SetZeroList:
    VoteFile[z] = 0

# reformat the vote history section into numbers instead of words, so they can be counted
primaryreformatlist = ['VH20G',
                       'VH18G',
                       'VH16G',
                       'VH14G']
for p in primaryreformatlist:
    VoteFile.loc[pd.notnull(VoteFile[p]), p] = 1
    VoteFile.loc[pd.isnull(VoteFile[p]), p] = 0

# create a voter frequency score to determine likelihood to vote in the upcoming election
# in my experience, these 3 elections predict voter turnout more accurately than the standard "x of 4" score which Datacenter calls "GeneralFrequency"
VoteFile['GovFreq'] = (VoteFile['VH20G']
                       + VoteFile['VH18G']
                       + VoteFile['VH14G'])

# tagging likely voters by party
VoteFile.loc[(((VoteFile['CalculatedParty'] == '1 - Hard Republican') |
               (VoteFile['CalculatedParty'] == '2 - Weak Republican'))
              & (VoteFile['GovFreq'] >= 2)),
             'LikelyTurnout_Rep'] = 1
VoteFile.loc[(((VoteFile['CalculatedParty'] == '5 - Hard Democrat') |
               (VoteFile['CalculatedParty'] == '4 - Weak Democrat'))
              & (VoteFile['GovFreq'] >= 2)),
             'LikelyTurnout_Dem'] = 1
VoteFile.loc[((VoteFile['CalculatedParty'] == '3 - Swing')
              & (VoteFile['GovFreq'] >= 2)),
             'LikelyTurnout_Swing'] = 1

# tagging GOTV Targets to determine if we can viably turn out enough Reps to overcome any deficit
VoteFile.loc[(((VoteFile['CalculatedParty'] == '1 - Hard Republican') |
               (VoteFile['CalculatedParty'] == '2 - Weak Republican'))
              & (VoteFile['GovFreq'] <= 1)),
             'GOTV_Targets'] = 1

# list of items to pivot below
PivotList = ['Registration',
             'LikelyTurnout_Rep',
             'LikelyTurnout_Dem',
             'LikelyTurnout_Swing',
             'GOTV_Targets']

# for each district in DistList above
for d in DistList:
    # create a blank report
    StateReport = pd.DataFrame()
    # then for each item in PivotList above
    for i in PivotList:
        # cut down the file to be pivoted to just the DistList and PivotList columns
        PivotData = VoteFile.loc[:, (d[0], i)].copy()

        # pivot the state with district as the rows, and the item as the column
        CountPivot = pd.pivot_table(PivotData,
                                    index=[d[0]],
                                    columns=[i],
                                    aggfunc=lambda x: (x > 0).count())
        # assign a new column in the report to the results of the pivot
        StateReport[i] = CountPivot.iloc(axis=1)[0:, 1].copy()
        # adding 0s to any blank lines, just to make things pretty
        for h in StateReport.columns:
            StateReport.loc[pd.isnull(StateReport[h]), h] = 0
    # add up the likely voters of each party
    StateReport['LikelyTurnout'] = (StateReport['LikelyTurnout_Rep'] +
                                    StateReport['LikelyTurnout_Dem'] +
                                    StateReport['LikelyTurnout_Swing'])
    # express each likely voter segment as a percentage
    StateReport['Likely_Rep%'] = (StateReport['LikelyTurnout_Rep'] /
                                  StateReport['LikelyTurnout'])
    StateReport['Likely_Swing%'] = (StateReport['LikelyTurnout_Swing'] /
                                    StateReport['LikelyTurnout'])
    StateReport['Likely_Dem%'] = (StateReport['LikelyTurnout_Dem'] /
                                  StateReport['LikelyTurnout'])
    # project the expected rep vote, after splitting the swing vote
    StateReport['RepDemSplit'] = (StateReport['LikelyTurnout_Rep'] /
                                  (StateReport['LikelyTurnout_Rep'] +
                                   StateReport['LikelyTurnout_Dem']))
    StateReport['ProjRep'] = (StateReport['LikelyTurnout_Rep'] +
                              (StateReport['LikelyTurnout_Swing'] *
                               StateReport['RepDemSplit']))
    StateReport['ProjRep%'] = (StateReport['ProjRep'] /
                               StateReport['LikelyTurnout'])
    # list the republican deficit, and the percentage of GOTV_Targets which will need to be turnout out to overcome that deficit
    StateReport['RepDeficit'] = ((StateReport['LikelyTurnout'] * .5) -
                                 StateReport['ProjRep'])
    StateReport['GOTV_Need'] = (StateReport['RepDeficit'] /
                                StateReport['GOTV_Targets'])

    # reformat the report to just be the columns we care about
    StateReport = StateReport[['Registration',
                               'LikelyTurnout',
                               'LikelyTurnout_Rep',
                               'Likely_Rep%',
                               'LikelyTurnout_Dem',
                               'Likely_Dem%',
                               'LikelyTurnout_Swing',
                               'Likely_Swing%',
                               'ProjRep',
                               'ProjRep%',
                               'RepDeficit',
                               'GOTV_Targets',
                               'GOTV_Need']].copy()

    # renaming the columns to be a little more descriptive.
    StateReport.columns = ['Registered Voters',
                           'Turnout',
                           'Rep Turnout',
                           'Rep %',
                           'Dem Turnout',
                           'Dem %',
                           'Swing Turnout',
                           'Swing %',
                           'Projected Rep',
                           'Projected Rep%',
                           'Deficit',
                           'GOTV Targets',
                           'GOTV Effectiveness Requirement']

    # Save the report as a CSV
    StateReport.to_csv(str(d[1]) + ' Report.csv')
