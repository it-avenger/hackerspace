import ast
import json

import random
from badges.models import Badge

from django.core.urlresolvers import reverse
from django.db import models
from django.utils import timezone

from quest_manager.models import Quest


class CytoElementQuerySet(models.query.QuerySet):
    def all_scape(self, scape_id):
        return self.filter(scape_id=scape_id)

    def all_parent(self, data_parent_id):
        return self.filter(data_parent_id=data_parent_id)

    def nodes(self):
        return self.filter(group=CytoElement.NODES)


class CytoElementManager(models.Manager):
    def get_queryset(self):
        return CytoElementQuerySet(self.model, using=self._db)

    def all_for_scape(self, scape):
        return self.get_queryset().all_scape(scape.id)

    def get_random_node(self, scape):
        qs = self.get_queryset().nodes().all_scape(scape.id)
        count = qs.count()
        random_index = random.randint(0, count - 1)
        return qs[random_index]

    def get_random_node_triangular_distribution(self, scape):
        qs = self.get_queryset().nodes().all_scape(scape.id)
        count = qs.count()
        random_index = int(random.triangular(0, count - 1, count / 2))
        return qs[random_index]

    def all_for_campaign(self, scape, data_parent):
        return self.all_for_scape(scape).all_parent(data_parent.id)


class CytoElement(models.Model):
    NODES = 'nodes'
    EDGES = 'edges'
    GROUP_CHOICES = ((NODES, 'nodes'), (EDGES, 'edges'))
    # name = models.CharField(max_length=200)
    scape = models.ForeignKey('CytoScape', on_delete=models.CASCADE)

    group = models.CharField(max_length=6, choices=GROUP_CHOICES, default=NODES)
    # TODO: make a callable for limit choices to, so that limited to nodes within the same scape
    data_parent = models.ForeignKey('self', blank=True, null=True, related_name="parents",
                                    limit_choices_to={'group': NODES},
                                    help_text="indicates the compound node parent; blank/null => no parent")
    data_source = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, related_name="sources",
                                    help_text="edge comes from this node")
    data_target = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, related_name="targets",
                                    help_text="edge goes to this node")
    data_dict = models.TextField(blank=True, null=True,
                                 help_text="python dictionary stored as string: {'key1':'value1', 'key2':'value2'}")
    selected = models.BooleanField(default=False)
    selectable = models.BooleanField(default=True)
    locked = models.BooleanField(default=False)
    grabbable = models.BooleanField(default=True)
    classes = models.CharField(max_length=250, blank=True, null=True,
                               help_text="a space separated list of css class names for the element")
    id_styles = models.TextField(blank=True, null=True,
                                 help_text="styles specific to this node (using id selector)")
    label = models.CharField(max_length=50, blank=True, null=True,
                             help_text="if present, will be used as node label instead of id")
    min_len = models.IntegerField(default=4,
                                  help_text="number of ranks to keep between the source and target of the edge")
    href = models.URLField(blank=True, null=True)

    objects = CytoElementManager()

    def __str__(self):
        return str(self.id) + ": " + self.label

    def get_data_dict(self):
        """:return data_dict text field as a python dictionary."""
        return ast.literal_eval(self.data_dict)

    def add_data(self, key, value):
        data = self.get_data_dict()
        data[key] = value
        self.data_dict = data
        self.save()

    def get_data(self, key):
        """:return the value for this key.  None if key doesn't exist."""
        data = self.get_data_dict()
        return data.get(key)

    def get_data_json(self):
        return json.dumps(self.data_dict)

    def has_parent(self):
        return self.data_parent is not None

    def is_edge(self):
        return self.data_source and self.data_target

    def is_node(self):
        return not self.is_edge()

    def json(self):
        json_str = "    {\n"
        # json_str +=         "      group: '" + self.group + "',\n"
        json_str += "      data: {\n"
        json_str += "        id: " + str(self.id) + ",\n"
        if self.label:
            json_str += "        label: '" + self.label + "',\n"
        if self.has_parent():
            json_str += "        parent: " + str(self.data_parent.id) + ",\n"
        elif self.is_edge():
            json_str += "        source: " + str(self.data_source.id) + ",\n"
            json_str += "        target: " + str(self.data_target.id) + ",\n"
            json_str += "        minLen: " + str(self.min_len) + ",\n"
            # json_str += "        edgeWeight: 1, \n"  # '" + str(self.edge_weight) + "',\n"
        if self.href:
            json_str += "        href: '" + self.href + "',\n"
        json_str += "      },\n "  # end data
        if self.classes:
            json_str += "     classes: '" + self.classes + "',\n"
        json_str += "    },\n "

        return json_str


class TempCampaign(object):
    """
    Temporary structure used to help build the cytoscape, generates lists for each campaign to make it easier to
    properly generate edges to give the desired layout.
    """
    def __init__(self, parent_node_id):
        self.node_id = parent_node_id
        self.child_node_ids = []  # Quests in the campaign
        self.reliant_node_ids = []  # Quests that rely on completion of quests in the campaign
        self.prereq_node_ids = []  # Quests that are required for quests in the campaign

    def __str__(self):
        tmp_str = "Parent: " + str(self.node_id)
        if self.child_node_ids:
            for child_id in self.child_node_ids:
                tmp_str += " Child:" + str(child_id)
        else:
            tmp_str += " No children"
        return tmp_str

    def add_child(self, child_node_id):
        self.child_node_ids.append(child_node_id)

    def add_reliant(self, reliant_node_id):
        self.reliant_node_ids.append(reliant_node_id)

    def add_prereq(self, prereq_node_id):
        # prereqs can't be in the campaign already, so check:
        if prereq_node_id not in self.child_node_ids:
            self.prereq_node_ids.append(prereq_node_id)

    def get_last_node_id(self):
        return self.child_node_ids[-1]

    def get_first_node_id(self):
        return self.child_node_ids[0]

    def get_first_prereq_id(self):
        return self.prereq_node_ids[0]

    def get_last_reliant_id(self):
        if self.reliant_node_ids:
            return self.reliant_node_ids[-1]
        else:
            return None

    def get_common_reliant_node_ids(self):
        """
        :return: return nodes that are reliant on ALL nodes within the campaign
        """
        num_children = len(self.child_node_ids)

        reliant_on_all_ids = []
        for reliant_id in set(self.reliant_node_ids):  # set( myList ) contains only unique values
            count = self.reliant_node_ids.count(reliant_id)
            if count == num_children:  # if all children point to the reliant node, consider it reliant on the campaign
                reliant_on_all_ids.append(reliant_id)
        return reliant_on_all_ids

    def get_common_prereq_node_ids(self):
        """
        :return: return nodes that are a prerequisite to ALL nodes within the campaign
        i.e. campaigns in which all quests become available concurrently
        """
        num_children = len(self.child_node_ids)

        prereq_for_all_ids = []
        for prereq_id in set(self.prereq_node_ids):
            count = self.prereq_node_ids.count(prereq_id)
            if count == num_children:  # if all children require this prereq, consider it a prereq for the campaign
                prereq_for_all_ids.append(prereq_id)
        return prereq_for_all_ids

    def prereq_is_within(self, prereq_id):
        return prereq_id in self.child_node_ids


class CytoScapeManager(models.Manager):
    def generate_random_tree_scape(self, name, size=100, container_element_id="cy"):
        scape = CytoScape(
            name=name,
            container_element_id=container_element_id,
            layout_name='breadthfirst',
            layout_options="directed: true, spacingFactor: " + str(1.75 * 30/size),
        )
        scape.save()

        # generate starting node
        mother_node = CytoElement(scape=scape, group=CytoElement.NODES,)
        mother_node.save()
        node_list = [mother_node]
        count = 1
        while node_list and count < size:
            current_node = random.choice(node_list)
            # 10% chance to split branch, 10% to cap it
            split = random.random()
            children = 1
            if split < .10:
                children = random.randint(1, 3) # 1 to 3

            if current_node is mother_node:
                children = 10
            if split < 90:  # create the target nodes, connect them to source, add them to list
                for i in range(0, children):
                    new_node = CytoElement(scape=scape, group=CytoElement.NODES, )
                    new_node.save()
                    node_list.append(new_node)
                    edge = CytoElement(
                        scape=scape, group=CytoElement.EDGES,
                        data_source=current_node,
                        data_target=new_node,
                    )
                    edge.save()
                    count += 1

            if len(node_list) > 1:  # don't cap last node
                node_list.remove(current_node)

        return scape

    def generate_random_scape(self, name, size=100, container_element_id="cy"):
        new_scape = CytoScape(
            name=name,
            container_element_id=container_element_id
        )
        new_scape.save()

        # generate nodes
        for i in range(0, size):
            new_node = CytoElement(
                scape=new_scape,
                group=CytoElement.NODES,
            )
            new_node.save()

        # generate edges
        for i in range(0, size * 3):
            new_edge = CytoElement(
                scape=new_scape,
                group=CytoElement.EDGES,
                data_source=CytoElement.objects.get_random_node(new_scape),
                data_target=CytoElement.objects.get_random_node(new_scape),
            )
            new_edge.save()

        return new_scape


class CytoScape(models.Model):
    name = models.CharField(max_length=250)
    initial_quest = models.OneToOneField(Quest)
    parent_scape = models.ForeignKey('self', blank=True, null=True,
                                     help_text="The scape preceding this one, so it can be linked back to")
    last_regeneration = models.DateTimeField(default=timezone.now)
    container_element_id = models.CharField(max_length=50, default="cy",
                                            help_text="id of the html element where the graph's canvas will be placed")
    layout_name = models.CharField(max_length=50, default="random",
                                   help_text="layout name according to cytoscape API: http://js.cytoscape.org/#layouts \
                                              null, random, preset, grid, circle, concentric, breadthfirst, cose, \
                                              add-ons: cola, dagre")
    layout_options = models.TextField(null=True, blank=True, help_text="key1: value1, key2: value2, ...")
    node_styles = models.TextField(null=True, blank=True,
                                   default="label: 'data(id)'",
                                   help_text="key1: value1, key2: value2, ...")
    edge_styles = models.TextField(null=True, blank=True, help_text="key1: value1, key2: value2, ...")
    parent_styles = models.TextField(null=True, blank=True, help_text="key1: value1, key2: value2, ...")

    quest_styles = ""
    badge_styles = quest_styles

    hidden_styles = "'opacity': 0.25,"
    link_styles = "'color':'#337ab7', "
    link_hover_styles = "'color':'#23527c',"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('djcytoscape:quest_map', kwargs={'quest_id': self.initial_quest_id})

    objects = CytoScapeManager()

    def json(self):
        elements = CytoElement.objects.all_for_scape(self)

        json_str = "cytoscape({ \n"
        json_str += "  container: document.getElementById('" + self.container_element_id + "'), \n"
        json_str += "  elements: [ \n"
        for element in elements:
            json_str += element.json()
        json_str += "  ], \n"
        json_str += "  layout: { \n"
        json_str += "    name: '" + self.layout_name + "', \n"
        if self.layout_options:
            json_str += self.layout_options
        json_str += "  }, \n"
        json_str += "  style: [ \n"
        if self.node_styles:
            json_str += self.get_selector_styles_json('node', self.node_styles)
        if self.edge_styles:
            json_str += self.get_selector_styles_json('edge', self.edge_styles)
        if self.parent_styles:
            json_str += self.get_selector_styles_json('$node > node', self.parent_styles)
        json_str += self.get_selector_styles_json('.Quest', self.quest_styles)
        json_str += self.get_selector_styles_json('.Badge', self.badge_styles)
        json_str += self.get_selector_styles_json('.hidden', self.hidden_styles)
        json_str += self.get_selector_styles_json('.link', self.link_styles)
        json_str += self.get_selector_styles_json('.link_hover', self.link_hover_styles)
        for element in elements:
            if element.id_styles:
                json_str += self.get_selector_styles_json('#'+str(element.id), element.id_styles)
        json_str += "  ], \n"
        # json_str += "  minZoom: 0.5, \n"
        # json_str += "  maxZoom: 1.5, \n"
        # json_str += "  userZoomingEnabled: false, \n"
        json_str += "});"

        return json_str

    @staticmethod
    def get_selector_styles_json(selector, styles):
        json_str = "    { \n"
        json_str += "      selector: '" + selector + "', \n"
        json_str += "      style: { \n"
        json_str += styles
        json_str += "      } \n"
        json_str += "    }, \n"
        return json_str

    @staticmethod
    def generate_label(obj):
        l = 30  # l = label length in characters
        post = ""
        pre = ""
        if type(obj) is Badge:
            pre = "Badge: "
        title = pre + str(obj)
        # shorten in the middle to fit within node_styles.width
        if len(title) > l:
            title = title[:(l-2)] + "..."  # + title[-int(l/2-2):]
        if hasattr(obj, 'xp'):
            post = " (" + str(obj.xp) + ")"
        return title + post

    def get_last_node_in_campaign(self, parent_node, offset=0):
        """
        :param offset: offset from last node by this (i.e. 1 --> second last node)
        :param parent_node: the compound node/parent, i.e. campaign
        :return: the most recent node added to the campaign (added to the compound/parent node) by using the highest id
        """
        try:
            # latest normally used with dates, but actually works with other fields too!
            # return CytoElement.objects.all_for_campaign(self, parent_node).latest('id')
            qs = CytoElement.objects.all_for_campaign(self, parent_node).order_by('-id')
            return qs[offset]
        except self.DoesNotExist:
            return None

    def add_node_from_object(self, obj, initial_node=False):
        # If node node doesn't exist already, create a new one
        new_node, created = CytoElement.objects.get_or_create(
            scape=self,
            group=CytoElement.NODES,
            label=self.generate_label(obj),
            classes=type(obj).__name__,
            id_styles="'background-image': '" + obj.get_icon_url() + "'"
            # defaults={'attribute': value},
        )

        # if this is a transition node (to a new map), add the link to href field. And add the "link" class
        if not initial_node and self.is_transition_node(new_node):
            new_node.href = reverse('maps:quest_map', args=[obj.id])
            new_node.classes += " link"
            new_node.save()

        return new_node, created

    def init_temp_campaign_list(self):
        """
        Create a new member variable `campaign_list` or clear it if it already exists
        """
        self.campaign_list = []

    def get_temp_campaign(self, campaign_id):
        for campaign in self.campaign_list:
            try:
                if campaign.node_id == campaign_id:
                    return campaign
            except ValueError:
                pass
        return None

    def add_to_campaign(self, obj, node, mother_node):
        """
        Checks if obj is in a campaign, if so, gets or creates the campaign_node (Parent/compound node)
        and adds is as the parent node.  Also registers the node and parent with the TempCampaign (for edges later)
        :param mother_node: prereq node
        :param obj:
        :param node: node of the object
        :return: campaign_node = None if obj isn't part of a campaign, otherwise = the campaign_node (i.e. parent_node)
        campaign_created = False if obj is in campaign, but the campaign was created by an earlier node
        """
        # If part of a campaign, create parent and add to "parent" node, i.e. compound node
        campaign_node = None
        campaign_created = False
        if hasattr(obj, 'campaign') and obj.campaign is not None:
            # parent_name = str(obj.campaign)
            campaign_node, campaign_created = CytoElement.objects.get_or_create(
                scape=self,
                group=CytoElement.NODES,
                label=str(obj.campaign),
                classes="campaign",
                # defaults={'attribute': value},
            )
            # Add parent
            node.data_parent = campaign_node
            node.save()

            # TempCampaign utility
            if campaign_created:
                self.campaign_list.append(TempCampaign(campaign_node.id))
            temp_campaign = self.get_temp_campaign(campaign_node.id)
            temp_campaign.add_child(node.id)
            temp_campaign.add_prereq(mother_node.id)

        return campaign_node, campaign_created

    def add_campaign_edges(self):
        """
        cyto dagre layout doesn't support compound/parent nodes, so we need to add invisible edges between parent nodes
        and first node in the campaign, for non-directed campaigns (i.e. all quests become available simultaneously)
        """
        for campaign in self.campaign_list:

            # If required, add the invisible edge connecting a prereq node to the campaign to help structure of map
            parent_node = CytoElement.objects.get(id=campaign.node_id)
            first_node_id = campaign.get_first_node_id()
            first_node = CytoElement.objects.get(id=first_node_id)
            prereq_node_ids = campaign.get_common_prereq_node_ids()
            if prereq_node_ids:
                for node_id in prereq_node_ids:
                    source_node = CytoElement.objects.get(id=node_id)
                    CytoElement.objects.get_or_create(
                        scape=self,
                        group=CytoElement.EDGES,
                        data_source=source_node,
                        data_target=first_node,
                        classes="hidden",
                        # defaults={'attribute': value},
                    )
                    # and add the visible node from prereq to campaign/compound/parent node
                    CytoElement.objects.get_or_create(
                        scape=self,
                        group=CytoElement.EDGES,
                        data_source=source_node,
                        data_target=parent_node,
                        # defaults={'attribute': value},
                    )
            else:  # add a visible edge between the first prereq and first child
                prereq_node_id = campaign.get_first_prereq_id()
                prereq_node = CytoElement.objects.get(id=prereq_node_id)
                CytoElement.objects.get_or_create(
                    scape=self,
                    group=CytoElement.EDGES,
                    data_source=prereq_node,
                    data_target=first_node,
                    # defaults={'attribute': value},
                )

            # If required, add the invisible edge connecting last campaign node to next node to help structure of map
            last_node_id = campaign.get_last_node_id()
            last_node = CytoElement.objects.get(id=last_node_id)
            reliant_node_ids = campaign.get_common_reliant_node_ids()
            if reliant_node_ids:
                for node_id in reliant_node_ids:
                    target_node = CytoElement.objects.get(id=node_id)
                    CytoElement.objects.get_or_create(
                        scape=self,
                        group=CytoElement.EDGES,
                        data_source=last_node,
                        data_target=target_node,
                        classes="hidden",
                        # defaults={'attribute': value},
                    )
                    # and add the visible node from campaign to next node
                    CytoElement.objects.get_or_create(
                        scape=self,
                        group=CytoElement.EDGES,
                        data_source=parent_node,
                        data_target=target_node,
                        # defaults={'attribute': value},
                    )
            else:  # add a visible edge between the last in campaign prereq and next node (if it exists)
                reliant_node_id = campaign.get_last_reliant_id()
                if reliant_node_id:
                    reliant_node = CytoElement.objects.get(id=reliant_node_id)
                    CytoElement.objects.get_or_create(
                        scape=self,
                        group=CytoElement.EDGES,
                        data_source=last_node,
                        data_target=reliant_node,
                        # defaults={'attribute': value},
                    )

    def add_reliant(self, current_obj, mother_node):
        reliant_objects = current_obj.get_reliant_objects()
        for obj in reliant_objects:
            # mother_node
            #  > obj (reliant node 1)
            #  > obj (reliant node 2)
            #  > ...

            # create the new reliant node if it doesn't already exist
            new_node, created = self.add_node_from_object(obj)
            source_node = mother_node
            classes = ""
            min_len = 4

            add_edge = True

            # if mother node is in a campaign/parent, add new_node as a reliant in the temp_campaign
            if mother_node.data_parent:
                temp_campaign = self.get_temp_campaign(mother_node.data_parent.id)
                temp_campaign.add_reliant(new_node.id)
                add_edge = False

            # add new_node to a campaign/compound/parent, if required
            campaign_node, campaign_created = self.add_to_campaign(obj, new_node, mother_node)

            if campaign_created:
                add_edge = False  # edges will be added later to connect campaigns

            if campaign_node and not campaign_created:  # Indicates an addition to an existing campaign
                add_edge = True
                # if this new node has a direct prereq from within the campaign, add edge, else add invisible edge
                temp_campaign = self.get_temp_campaign(new_node.data_parent.id)
                if temp_campaign.prereq_is_within(mother_node.id):  # mother = prereq
                    source_node = mother_node
                else:
                    source_node = self.get_last_node_in_campaign(campaign_node, 1)
                    classes = "hidden"
                    min_len = 1

            # if new campaign, or mother_node is ina campaign, edges will be added later with .add_campaign_edges()
            if add_edge:
                CytoElement.objects.get_or_create(
                    scape=self,
                    group=CytoElement.EDGES,
                    data_source=source_node,
                    data_target=new_node,
                    classes=classes,
                    min_len=min_len,
                    # defaults={'attribute': value},
                )

            # If repeatable, add circular edge
            if hasattr(obj, 'max_repeats'):
                if obj.max_repeats != 0:
                    repeat_edge = CytoElement(
                        scape=self, group=CytoElement.EDGES,
                        data_source=new_node,
                        data_target=new_node,
                    )
                    repeat_edge.save()

            # recursive, continuing adding if this is a new node, and not a closing node
            if created and not self.is_transition_node(new_node):
                self.add_reliant(obj, new_node)

    @staticmethod
    def is_transition_node(node):
        return node.label[0] is "~"

    @staticmethod
    def generate_map(initial_quest, name, container_element_id="cy", layout_name="dagre"):

        layout_options = "'nodeSep': 25, "\
                         "'rankSep': 10, "\
                         "'minLen': function( edge ){ return edge.data('minLen'); }," \
                         "" \
                         "" \
                         ""

        # "'directed': 'true', " \
        # "'spacingFactor': '1.5', " \
        # "'padding': '100', " \

        node_styles = "label: 'data(label)'," \
                      "'text-valign': 'center', " \
                      "'text-halign': 'right', " \
                      "'background-fit': 'cover'," \
                      "'shape': 'rectangle'," \
                      "'background-opacity': 0," \
                      "'padding-right':10," \
                      "'padding-left':5," \
                      "'padding-top':5," \
                      "'padding-bottom':5," \
                      "'text-events':'yes'," \
                      ""

        # node_styles = "label: 'data(label)'," \
        #               "'shape': 'roundrectangle'," \
        #               "'background-opacity': '1'," \
        #               "'background-color':'lightgray'," \
        #               "'border-color': 'black', " \
        #               "'border-width': '1', " \
        #               "'padding-top': '10px', " \
        #               "'padding-bottom': '10px', " \
        #               "'padding-left': '10px', " \
        #               "'padding-right': '10px', " \
        #               "'text-valign': 'center', "\
        #               "'width': '245px', " \
        #               "'height': 'label', " \
        #               ""

        edge_styles = "'width': 1, "\
                      "'curve-style':'bezier', " \
                      "'line-color': 'black', " \
                      "'line-style': 'solid', "\
                      "'target-arrow-shape': 'triangle-backcurve', "\
                      "'target-arrow-color':'black', "\
                      "'text-rotation': 'autorotate', "\
                      ""

        parent_styles = "'text-rotation': '-90deg'," \
                        "'text-halign': 'left'," \
                        "'text-margin-x': -10," \
                        "'text-margin-y': -50," \
                        ""

        scape = CytoScape(
            name=name,
            initial_quest=initial_quest,
            container_element_id=container_element_id,
            layout_name=layout_name,
            layout_options=layout_options,
            node_styles=node_styles,
            edge_styles=edge_styles,
            parent_styles=parent_styles,
        )
        scape.save()

        scape.calculate_nodes()

        # # generate starting node
        # mother_node, created = scape.add_node_from_object(initial_quest)
        #
        # # node_list = [mother_node]
        #
        # scape.init_temp_campaign_list()
        # scape.add_reliant(initial_quest, mother_node)
        # scape.add_campaign_edges()
        return scape

    def calculate_nodes(self):
        # Create the starting node from the initial quest
        mother_node, created = self.add_node_from_object(self.initial_quest, initial_node=True)
        # Temp campaign list used to track funky edges required for compound nodes to display properly with dagre
        self.init_temp_campaign_list()
        # Add nodes reliant on the mother_node, this is recursive and will generate all nodes until endpoints reached
        # Endpoints... not sure yet, but probably quests starting with '~' tilde character, or add a new field?
        self.add_reliant(self.initial_quest, mother_node)
        # Add those funky edges for proper display of compound (parent) nodes in cyto dagre layout
        self.add_campaign_edges()
        self.last_regeneration = timezone.now()
        self.save()

    def regenerate(self):
        # Delete existing nodes
        CytoElement.objects.all_for_scape(self).delete()
        self.calculate_nodes()

