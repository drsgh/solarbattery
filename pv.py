import pandas as pd
import matplotlib.pyplot as mpl

class PvSystem:
# initialization functions
    def __init__(self, dc, dcCol, ac, prodFile, curveFile, curveCombineIndex):
        self.dc = dc
        self.dcCol = dcCol
        self.ac = ac
        self.prodFile = prodFile
        self.curveFile = curveFile
        self.revTable = combineFiles(prodFile,curveFile,curveCombineIndex)

    def initRev(self):
        self.revTable.loc[:, 'solarRev'] = self.revTable['dsmRate'] * self.revTable['dsmKwhAlt']

    def initRate(self, rateComponentsArray):
        self.revTable.loc[:, 'dsmRate'] = 0
        for comp in rateComponentsArray:
            self.revTable.loc[:, 'dsmRate'] = self.revTable[comp] + self.revTable['dsmRate']
        #self.revTable.plot(x="day", y="dsmRate")
        #mpl.show()

    def initGen(self):
        self.revTable.loc[:, 'dsmKwhAlt'] = 0
        self.revTable.loc[:, 'dsmKwhAltLimit'] = self.ac * 1000
        self.revTable.loc[:, 'dsmKwhAlt'] = self.revTable[[self.dcCol, 'dsmKwhAltLimit']].min(axis=1)
        self.revTable.loc[:, 'dsmKwhDirVersusLimit'] = self.revTable.loc[:, 'dckwh'] - self.revTable.loc[:, 'dsmKwhAltLimit']
        self.revTable.loc[:, 'dsmKwhDirUnderLimit'] = self.revTable.loc[:, 'dckwh'] - self.revTable.loc[:, 'dsmKwhAltLimit']
        self.revTable.loc[self.revTable['dsmKwhDirVersusLimit'] < 0, 'dsmKwhDirVersusLimit'] = 0
        self.revTable.loc[self.revTable['dsmKwhDirUnderLimit'] > 0, 'dsmKwhDirUnderLimit'] = 0

    def addCurveRank(self):
        self.revTable['dsmCurveHourRank'] = self.revTable.groupby('day')['dsmRate'].rank(ascending=False)

    def applyProbGen(self):
        self.revTable.loc[:, 'minGen'] = 0
        self.revTable.loc[:, 'maxGen'] = 0

    def initBattery(self):
        self.revTable.loc[:, 'batteryState'] = 0
        self.revTable.loc[:, 'batteryStartingCharge'] = 0

    def chargeRules(self, rules):
        ruleSet = rules[0]
        if ruleSet['hourEnd']:
            self.revTable.loc[:, 'hourEnd'] = 1
            self.revTable.loc[self.revTable['hourday'] > ruleSet['hourEnd'], 'hourEnd'] = 0

    def dischargeRules(self, rules):
        ruleSet = rules[0]
        if ruleSet['hourStart']:
            self.revTable.loc[:, 'hourStart'] = 1
            self.revTable.loc[self.revTable['hourday'] < ruleSet['hourStart'], 'hourStart'] = 0

    def setChargeHours(self, rules):
        ruleSet = rules
        self.revTable.loc[:, 'chargeHour'] = 1
        for i in range(0, len(ruleSet)):
            self.revTable.loc[:, 'chargeHour'] = self.revTable.loc[:, 'chargeHour'] * self.revTable.loc[:, ruleSet[i]]

    def addChargeHourRank(self):
            self.revTable['dsmChargeHourRank'] = self.revTable.loc[self.revTable['chargeHour'] == 1].groupby('day')['dsmRate'].rank(ascending=True)

    def setDischargeHours(self, rules):
        ruleSet = rules
        self.revTable.loc[:, 'dischargeHour'] = 1
        for i in range(0, len(ruleSet)):
            self.revTable.loc[:, 'dischargeHour'] = self.revTable.loc[:, 'dischargeHour'] * self.revTable.loc[:, ruleSet[i]]

    def addDischargeHourRank(self):
            self.revTable['dsmDischargeHourRank'] = self.revTable.loc[self.revTable['dischargeHour'] == 1].groupby('day')['dsmRate'].rank(ascending=False)

    def addDailyCumClipping(self):
        self.revTable['dsmDailyCumGen'] = self.revTable.groupby('day')['dckwh'].cumsum()
        self.revTable['dsmDailyCumClipping'] = self.revTable.groupby('day')['dsmKwhDirVersusLimit'].cumsum()
        self.revTable['dsmDailyTotalClipping'] = self.revTable.groupby('day')['dsmKwhDirVersusLimit'].transform('sum')
        self.revTable['dsmAvailClipping'] = self.revTable.loc[:, 'dsmKwhDirVersusLimit']
        self.revTable.loc[self.revTable['chargeHour'] == 0, 'dsmAvailClipping'] = 0
        self.revTable['dsmDailyAvailCumClipping'] = self.revTable.loc[self.revTable['chargeHour'] == 1].groupby('day')['dsmAvailClipping'].cumsum()
        self.revTable['dsmDailyAvailTotalClipping'] = self.revTable.loc[self.revTable['chargeHour'] == 1].groupby('day')['dsmAvailClipping'].transform('sum')

    def prepareForBatteryCycles(self):
        self.revTable['resClippedDischarge'] = 0
        self.revTable['resPaidDischarge'] = 0
        self.revTable['resTotalDischarge'] = 0
        self.revTable['resClippedCharge'] = 0
        self.revTable['resPaidCharge'] = 0
        self.revTable['resTotalCharge'] = 0

        self.revTable['resClippedGrossCharge'] = 0
        self.revTable['resPaidGrossCharge'] = 0
        self.revTable['resTotalGrossCharge'] = 0
        self.revTable['resClippedGrossDischarge'] = 0
        self.revTable['resPaidGrossDischarge'] = 0
        self.revTable['resTotalGrossDischarge'] = 0

        self.revTable['resClippedChargeAllocated'] = 0
        self.revTable['resPaidChargeAllocated'] = 0

        self.revTable['resClippedDischargeValue'] = 0
        self.revTable['resPaidDischargeValue'] = 0


def combineFiles(file1, file2, index2):
    df1 = pd.read_csv(file1, index_col=0, header=0)
    df2 = pd.read_csv(file2, index_col=0, header=0)
    mergedFile = df2.merge(df1, on=index2, how='left')
    return mergedFile

prodFile = r'.\dc-5000_kwhkw-1298.csv'
curveFile = r'.\curve_alt_2_8760.csv'
#usagetable = pd.read_csv(genfile, index_col=0, header=0)

# initiate PV System
sys = PvSystem(5, 'dckwh', 4, prodFile, curveFile, 'houryear')
battMw = 4
battMwh = 4
battKwh = battMwh * 1000
chargeEff = 0.90
dischargeEff = 0.90
inverterEff = 0.96
batteryHours = battMwh / battMw
batteryCycleLife = 3000
batteryCostPerKw = 200
costPerCycle = (batteryCostPerKw * battKwh) / batteryCycleLife

PvSystem.initRate(sys, ['lbmp', 'drv', 'icap', 'e'])
PvSystem.initGen(sys)
PvSystem.initRev(sys)
PvSystem.addCurveRank(sys)
PvSystem.initBattery(sys)
PvSystem.chargeRules(sys, [{'hourEnd': 13}])
PvSystem.dischargeRules(sys, [{'hourStart': 13}])
PvSystem.setChargeHours(sys, ['hourEnd'])
PvSystem.setDischargeHours(sys, ['hourStart'])
PvSystem.addChargeHourRank(sys)
PvSystem.addDischargeHourRank(sys)
PvSystem.addDailyCumClipping(sys)
PvSystem.prepareForBatteryCycles(sys)

# 24 hour cycle

hours = len(sys.revTable.index)
days = len(sys.revTable.groupby('day'))

# cycle through 24 hour periods
#### Need to restrict charging and discharging to the mw size of battery

for day in range(1, days):
    maxBatteryPotential = battMwh*1000
    dayData = sys.revTable[sys.revTable['day'] == day]
    batteryStartingCharge = dayData.loc[dayData['hourday'] == 1, 'batteryState'].item()
    sys.revTable.loc[sys.revTable['day'] == day, 'batteryStartingCharge'] = batteryStartingCharge
    availableDailyClipping = dayData.loc[dayData['hourday'] == 1, 'dsmDailyAvailTotalClipping'].item()
    expectedDailyClipping = availableDailyClipping

    # determine max charge for the day
    availableCharge = batteryStartingCharge + availableDailyClipping
    for chargeHour in range(1, 24 + 1):
       if dayData.loc[dayData['dsmChargeHourRank'] == chargeHour].empty == False:
           availableCharge = availableCharge + dayData.loc[dayData['dsmChargeHourRank'] == chargeHour, 'dckwh'].item()

    batteryPotentialDischarge = min(availableCharge, maxBatteryPotential)
    uncappedDischarge = 0

# distribute the available clipped energy first
    for dischargeHour in range(1, 24 + 1):
        if availableDailyClipping > 0 and batteryPotentialDischarge > 0:
            inverterKwhSpace = dayData.loc[dayData['dsmDischargeHourRank'] == dischargeHour, 'dsmKwhDirUnderLimit'].item() * -1
            clippingAllocatedToHour = min(inverterKwhSpace, availableDailyClipping)
            availableDailyClipping = availableDailyClipping - clippingAllocatedToHour
            dayData.loc[dayData['dsmDischargeHourRank'] == dischargeHour, 'resClippedDischarge'] = clippingAllocatedToHour
            dayData.loc[dayData['dsmDischargeHourRank'] == dischargeHour, 'dsmKwhDirUnderLimit'] = -inverterKwhSpace + clippingAllocatedToHour
            batteryPotentialDischarge = batteryPotentialDischarge - clippingAllocatedToHour
            uncappedDischarge = uncappedDischarge + clippingAllocatedToHour

# distribute remaining energy
    for dischargeHour in range(1, 24 + 1):
        if dayData.loc[dayData['dsmDischargeHourRank'] == dischargeHour].empty == False:
            if batteryPotentialDischarge > 0:
                inverterKwhSpace = dayData.loc[dayData['dsmDischargeHourRank'] == dischargeHour, 'dsmKwhDirUnderLimit'].item() * -1
                dischargeAllocatedToHour = min(inverterKwhSpace, batteryPotentialDischarge)
                batteryPotentialDischarge = batteryPotentialDischarge - dischargeAllocatedToHour
                dayData.loc[dayData['dsmDischargeHourRank'] == dischargeHour, 'resPaidDischarge'] = dischargeAllocatedToHour
                dayData.loc[dayData['dsmDischargeHourRank'] == dischargeHour, 'dsmKwhDirUnderLimit'] = -inverterKwhSpace + dischargeAllocatedToHour
                dayData.loc[dayData['dsmDischargeHourRank'] == dischargeHour, 'resTotalDischarge'] = dischargeAllocatedToHour + dayData.loc[dayData['dsmDischargeHourRank'] == dischargeHour, 'resClippedDischarge'].item()
                uncappedDischarge = uncappedDischarge + dischargeAllocatedToHour

# charge from the available clipped energy first
    maxPotentialNewCharge = min(maxBatteryPotential-batteryStartingCharge, uncappedDischarge)
    newChargeAllocatedTotal = 0
    for chargeHour in range(1, 24 + 1):
        if expectedDailyClipping > 0:
            if dayData.loc[dayData['dsmChargeHourRank'] == chargeHour].empty == False:
                availableClipping = dayData.loc[dayData['dsmChargeHourRank'] == chargeHour, 'dsmAvailClipping'].item()
                newChargeAllocated = min(availableClipping * chargeEff, maxPotentialNewCharge - newChargeAllocatedTotal)
                newChargeAllocatedTotal = newChargeAllocatedTotal + newChargeAllocated
                dayData.loc[dayData['dsmChargeHourRank'] == chargeHour, 'resClippedCharge'] = newChargeAllocated

# charge from the remaining available energy
    for chargeHour in range(1, 24 + 1):
        if dayData.loc[dayData['dsmChargeHourRank'] == chargeHour].empty == False:
            availableClipping = dayData.loc[dayData['dsmChargeHourRank'] == chargeHour, 'dsmAvailClipping'].item()
            additionalCharge = dayData.loc[dayData['dsmChargeHourRank'] == chargeHour, 'dckwh'].item() - availableClipping
            newChargeAllocated = min(additionalCharge * chargeEff, maxPotentialNewCharge - newChargeAllocatedTotal)
            newChargeAllocatedTotal = newChargeAllocatedTotal + newChargeAllocated
            dayData.loc[dayData['dsmChargeHourRank'] == chargeHour, 'resPaidCharge'] = newChargeAllocated
            dayData.loc[dayData['dsmChargeHourRank'] == chargeHour, 'resTotalCharge'] = newChargeAllocated + dayData.loc[dayData['dsmChargeHourRank'] == chargeHour, 'resClippedCharge'].item()

# add revenue ranks
    for dischargeHour in range(1, 24 + 1):
        if dayData.loc[dayData['dsmDischargeHourRank'] == dischargeHour].empty == False:
            dischargeKwh = dayData.loc[dayData['dsmDischargeHourRank'] == dischargeHour, 'resTotalDischarge'].item()
            dischargeKwhAllocated = 0
            dischargeKwhRemaining = dischargeKwh

            dischargeCurveValue = dayData.loc[dayData['dsmDischargeHourRank'] == dischargeHour, 'curve'].item()
            dischargeValue = dischargeKwh * dischargeCurveValue
            dischargeValueAllocated = 0
            dischargeValueRemaining = dischargeValue

        # allocate clipped charge first
            for chargeHour in range(1, 24 + 1):
                if dayData.loc[dayData['dsmChargeHourRank'] == chargeHour].empty == False:
                    if dischargeKwhRemaining > 0:
                        chargeClipped = dayData.loc[dayData['dsmChargeHourRank'] == chargeHour, 'resClippedCharge'].item()
                        chargeClippedAllocatedTotal = dayData.loc[dayData['dsmChargeHourRank'] == chargeHour, 'resClippedChargeAllocated'].item()
                        chargeClippedRemaining = chargeClipped - chargeClippedAllocatedTotal
                        chargeClippedAllocated = min(dischargeKwhRemaining, chargeClippedRemaining)
                        dischargeKwhRemaining = dischargeKwhRemaining - chargeClippedAllocated
                        dayData.loc[dayData['dsmChargeHourRank'] == chargeHour, 'resClippedChargeAllocated'] = chargeClippedAllocatedTotal + chargeClippedAllocated
                        dayData.loc[dayData['dsmChargeHourRank'] == chargeHour, 'resClippedDischargeValue'] = (dischargeCurveValue * chargeClippedAllocated) + dayData.loc[dayData['dsmChargeHourRank'] == chargeHour, 'resClippedDischargeValue']

        # allocate rem charge
            for chargeHour in range(1, 24 + 1):
                if dayData.loc[dayData['dsmChargeHourRank'] == chargeHour].empty == False:
                    if dischargeKwhRemaining > 0:
                        chargePaid = dayData.loc[dayData['dsmChargeHourRank'] == chargeHour, 'resPaidCharge'].item()
                        chargePaidAllocatedTotal = dayData.loc[dayData['dsmChargeHourRank'] == chargeHour, 'resPaidChargeAllocated'].item()
                        chargePaidRemaining = chargePaid - chargePaidAllocatedTotal
                        chargePaidAllocated = min(dischargeKwhRemaining, chargePaidRemaining)
                        dischargeKwhRemaining = dischargeKwhRemaining - chargePaidAllocated
                        dayData.loc[dayData['dsmChargeHourRank'] == chargeHour, 'resPaidChargeAllocated'] = chargePaidAllocatedTotal + chargePaidAllocated
                        dayData.loc[dayData['dsmChargeHourRank'] == chargeHour, 'resPaidDischargeValue'] = (dischargeCurveValue * chargePaidAllocated) + dayData.loc[dayData['dsmChargeHourRank'] == chargeHour, 'resPaidDischargeValue']


    sys.revTable.loc[sys.revTable['day'] == day, :] = dayData

sys.revTable.loc[:, 'resClippedGrossCharge'] = sys.revTable.loc[:, 'resClippedGrossCharge'] / chargeEff
sys.revTable.loc[:, 'resPaidGrossCharge'] = sys.revTable.loc[:, 'resPaidGrossCharge'] / chargeEff
sys.revTable.loc[:, 'resTotalGrossCharge'] = sys.revTable.loc[:, 'resTotalGrossCharge'] / chargeEff
sys.revTable.loc[:, 'resClippedGrossDischarge'] = sys.revTable.loc[:, 'resClippedGrossDischarge'] / dischargeEff
sys.revTable.loc[:, 'resPaidGrossDischarge'] = sys.revTable.loc[:, 'resPaidGrossDischarge'] / dischargeEff
sys.revTable.loc[:, 'resTotalGrossDischarge'] = sys.revTable.loc[:, 'resTotalGrossDischarge'] / dischargeEff

save_path = r'.'
sys.revTable.to_csv(save_path + '\\' + 'revTable.csv')







