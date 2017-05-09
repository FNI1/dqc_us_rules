# (c) Copyright 2015 - 2017, XBRL US Inc. All rights reserved.
# See https://xbrl.us/dqc-license for license information.
# See https://xbrl.us/dqc-patent for patent infringement notice.
import os
import csv
from .util import messages
from arelle.PythonUtil import attrdict
from arelle.ValidateXbrlCalcs import roundFact


_CODE_NAME = 'DQC.US.0011'
_RULE_VERSION = '3.3.0'
_DQC_11_ITEMS_FILE = os.path.join(
    os.path.dirname(__file__),
    'resources',
    'DQC_US_0011',
    'dqc_0011.csv'
)
_NO_FACT_KEY = 'no_fact'


def run_checks(val):
    """
    Entrypoint for the rule.  Load the config, search for instances of
    reversed calculation relationships.

    :param val: val from which to gather end dates
    :type val: :class:'~arelle.ModelXbrl.ModelXbrl'
    :return: No direct return
    :rtype: None
    """
    model_xbrl = val.modelXbrl
    for check in _load_checks(model_xbrl):
        rule_index_key = check.rule_num
        try:  # allow exceptions when no fact or concept for QName
            for n_fact in model_xbrl.factsByQname[check.nondim_concept]:
                # here want dimensionless line items only
                if not n_fact.context.qnameDims:
                    # find fact expressed with dimensions
                    for d_fact in model_xbrl.factsByQname[check.dim_concept]:
                        if (_check_for_exclusions(d_fact)):
                            d_fact_mem = d_fact.context.dimMemberQname(
                                check.axis)
                            if (d_fact_mem == check.member and
                                n_fact.context.isPeriodEqualTo(
                                    d_fact.context
                                ) and
                                n_fact.context.isEntityIdentifierEqualTo(
                                    d_fact.context
                                ) and
                                n_fact.unit.isEqualTo(d_fact.unit) and
                                    roundFact(n_fact,
                                              True) != roundFact(d_fact,
                                                                 True) *
                                    check.weight):
                                val.modelXbrl.error(
                                    '{base_key}.{extension_key}'.format(
                                        base_key=_CODE_NAME,
                                        extension_key=rule_index_key
                                    ),
                                    messages.get_message(_CODE_NAME,
                                                         _NO_FACT_KEY),
                                    modelObject=(n_fact, d_fact),
                                    weight=check.weight,
                                    ruleVersion=_RULE_VERSION
                                )
        except (IndexError, KeyError):
            # no facts to gripe about for this check
            pass


def _load_checks(model_xbrl):
    """
    Returns a map of line items and dim items to test

    :rtype: dict by line item name of dim, line item, axis, member and weight
    """
    def _qname(local_name):
        # just get qname of concept, or None if no such local name is a concept
        try:
            return model_xbrl.nameConcepts[local_name][0].qname
        except (KeyError, IndexError):
            return None
    try:
        with open(_DQC_11_ITEMS_FILE, 'rt') as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            return [attrdict(
                rule_num=int(row[0]),
                nondim_concept=_qname(row[1]),
                dim_concept=_qname(row[2]),
                axis=_qname(row[3]),
                member=_qname(row[4]),
                weight=int(row[5])
            )
                    for row in reader]
    except (FileNotFoundError, ValueError):
        return ()


def _check_for_exclusions(fact):
    """
    Checks facts to determine whether the facts contains members or axes we
    do not want to check

    :param fact: fact to check
    :type fact: :class:'~arelle.InstanceModelObject.ModelFact'
    :return: False (so we don't continue) if the fact contains exclusion
        criteria.
        True (so we do continue) otherwise.
    :rtype: bool
    """
    for fact_axis, fact_dim_value in fact.context.segDimValues.items():
        if not fact_dim_value.isTyped and ('ScenarioPreviouslyReportedMember'
                == fact_dim_value.memberQname.localName
                or 'LegalEntityAxis' == fact_axis.qname.localName
                or ('StatementScenarioAxis' == fact_axis.qname.localName
                    and ('RestatementAdjustmentMember'
                        == fact_dim_value.memberQname.localName
                        or 'ScenarioPreviouslyReportedMember'
                            == fact_dim_value.memberQname.localName
                        )
                    )
                ):
            return False
    return True


__pluginInfo__ = {
    'name': _CODE_NAME,
    'version': _RULE_VERSION,
    'description': 'Calcs reversed checks.',
    # Mount points
    'Validate.XBRL.Finally': run_checks,
}
